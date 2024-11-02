import sys
from PySide2 import QtGui, QtCore, QtWidgets
from PySide2.QtCore import Qt
from pxr import Usd

HEADER_LABELS = ["Name", "Type", "Kind", "Variants", "Active"]
HEADER_WIDTH = [350, 50, 70, 100, 50, 50]

DEFAULT_VARIANTS = {
    "Select No Variant": ""
}


class PrimItem(QtGui.QStandardItem):
    VARIANT_ROLE = QtCore.Qt.UserRole + 10
    PRIM_ROLE = QtCore.Qt.UserRole + 20
    PRIM_ITEM_ROLE = QtCore.Qt.UserRole + 30

    def __init__(self, prim, predicate=Usd.PrimIsActive):
        super().__init__()
        self.prim = prim
        self.predicate = predicate
        self.setText(prim.GetName())
        self.setIcon(QtGui.QIcon(""))
        self.children_prims = prim.GetFilteredChildren(self.predicate)

    def update_role_data(self, parent_item):
        if not parent_item.model():
            return

        item = parent_item.model().itemFromIndex(
            parent_item.index().sibling(parent_item.index().row(), HEADER_LABELS.index("Variants")))
        variants = self.variant_info(parent_item.prim)
        variants_str = " - ".join([f"{var}: {variants[var].get('default_variant', '')}" for var in variants])
        item.setText(variants_str)

        item.setData(variants, PrimItem.VARIANT_ROLE)
        parent_item.setData(parent_item.prim, PrimItem.PRIM_ROLE)
        item.setData(parent_item, PrimItem.PRIM_ITEM_ROLE)

        parent_item.model().dataChanged.emit(parent_item.index(), item.index())

    def setup_item(self, prim):
        prim_item = PrimItem(prim, self.predicate)
        descendants_item = QtGui.QStandardItem(str(prim_item.children_count))
        type_item = QtGui.QStandardItem(prim.GetTypeName())
        kind_item = QtGui.QStandardItem(Usd.ModelAPI(prim).GetKind())
        variant_item = QtGui.QStandardItem("")
        active_item = QtGui.QStandardItem(str(prim.IsActive()))

        self.children_prims = prim.GetFilteredChildren(self.predicate)
        return [prim_item, type_item, kind_item, variant_item, active_item]

    @property
    def children_count(self):
        return len(self.children_prims)

    def append_children(self, prim):
        row_count = self.rowCount()
        if row_count > 0:
            self.removeRows(0, row_count)

        for child_prim in prim.GetFilteredChildren(self.predicate):
            row = self.setup_item(child_prim)
            self.appendRow(row)
            self.update_role_data(row[0])

        self.children_prims = []
        self.update_role_data(self)

    def set_variant(self, variant_set, variant_name):
        variant_set = self.prim.GetVariantSets().GetVariantSet(variant_set)
        variant_set.SetVariantSelection(variant_name)

    def variant_info(self, prim):
        variant_info = {}
        variant_sets = prim.GetVariantSets()
        variant_set_names = variant_sets.GetNames()

        for variant_set_name in variant_set_names:
            variant_set = variant_sets.GetVariantSet(variant_set_name)
            all_variants = variant_set.GetVariantNames()

            default_variant = variant_set.GetVariantSelection() or ""
            variant_info[variant_set_name] = {
                "variants": all_variants,
                "default_variant": default_variant
            }

        return variant_info


class PrimTreeModel(QtGui.QStandardItemModel):
    def __init__(self):
        super().__init__()

    def hasChildren(self, parent):
        if super().hasChildren(parent):
            return True

        item = self.itemFromIndex(parent)
        if isinstance(item, PrimItem):
            return item.children_count > 0
        return False

    def canFetchMore(self, parent):
        item = self.itemFromIndex(parent)
        if isinstance(item, PrimItem):
            return item.children_count > 0
        return False

    def fetchMore(self, parent):
        item = self.itemFromIndex(parent)
        if isinstance(item, PrimItem):
            item.append_children(item.prim)


class PrimTreeView(QtWidgets.QTreeView):
    def __init__(self, prim_range, predicate=Usd.PrimIsActive, parent=None):
        super().__init__(parent)
        self._is_all_expanded = False
        self.prim_range = iter(prim_range)
        self.root_item = PrimItem(next(self.prim_range), predicate)

        self.tree_model = PrimTreeModel()
        self.tree_model.setHorizontalHeaderLabels(HEADER_LABELS)
        self.tree_model.appendRow(self.root_item)
        self.setModel(self.tree_model)

        self.setUniformRowHeights(True)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        self.expanded.connect(self._expand)
        self.collapsed.connect(self._collapse)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

        for i, width in enumerate(HEADER_WIDTH):
            self.setColumnWidth(i, width)

        self.setExpanded(self.root_item.index(), True)

        self.apply_stylesheet()

    def _expand(self, index):
        if not self._is_all_expanded:
            return
        for i in range(0, self.model().rowCount(index)):
            child = self.model().index(i, 0, index)
            if not self.model().hasChildren(index):
                continue
            self.setExpanded(child, True)
            self._expand(child)

    def _collapse(self, index):
        if not self._is_all_expanded:
            return
        for i in range(0, self.model().rowCount(index)):
            child = self.model().index(i, 0, index)
            if self.isExpanded(child):
                self.setExpanded(child, False)
                self._collapse(child)

    def context_menu(self, position):
        index = self.indexAt(position)
        if not index.isValid():
            return

        menu = QtWidgets.QMenu(self)

        item = self.model().itemFromIndex(index)
        row_item = self.model().itemFromIndex(index.sibling(index.row(), 0))

        copy_paths_action = QtWidgets.QAction("Copy Paths")
        menu.addAction(copy_paths_action)

        copy_paths_action.triggered.connect(lambda status=True, item=row_item: self.on_copy_paths(status, item=item))

        variants = item.data(PrimItem.VARIANT_ROLE)
        if variants:
            for var_set in variants:
                var_set_menu = QtWidgets.QMenu(var_set)
                action_group = QtWidgets.QActionGroup(var_set_menu)
                action_group.setExclusive(True)

                variant_names = variants[var_set].get("variants", [])
                variant_names.append("---")
                variant_names.extend(DEFAULT_VARIANTS.keys())
                for var_name in variant_names:
                    if var_name == "---":
                        var_set_menu.addSeparator()
                        continue
                    var_name_action = QtWidgets.QAction(var_name, var_set_menu)

                    var_name = DEFAULT_VARIANTS.get(var_name, var_name)
                    var_name_action.triggered.connect(
                        lambda status=True, action=var_name_action, var_set=var_set, var_name=var_name, item=row_item:
                        self.on_variant_selected(status, var_set=var_set, var_name=var_name, item=item)
                    )

                    var_name_action.setCheckable(True)
                    action_group.addAction(var_name_action)

                    if var_name == variants[var_set].get("default_variant", ""):
                        var_name_action.setChecked(True)

                    var_set_menu.addAction(var_name_action)

                menu.addMenu(var_set_menu)

        menu.exec_(self.viewport().mapToGlobal(position))

    def on_variant_selected(self, status, var_set, var_name, item):
        if status:
            item.set_variant(var_set, var_name)
            item.append_children(item.prim)
            self.model().dataChanged.emit(item.index(), item.index())

    def on_copy_paths(self, status, item):
        _prim_paths = []
        for i in self.selectedIndexes():
            if i.isValid():
                _item = self.model().itemFromIndex(i)
                _prim = _item.data(PrimItem.PRIM_ROLE)
                if _prim:
                    _prim_paths.append(_prim.GetPath().pathString)

        paths_clipboard = " ".join(_prim_paths)
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(paths_clipboard)

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QTreeView {
                background-color: #2d2d2d; 
                alternate-background-color: #3c3c3c;  
                color: #f0f0f0; 
                font-size: 12px;
                font-weight: normal;
            }
            QHeaderView::section {
                background-color: #444444;  
                color: #f0f0f0;  
                font-weight: bold;
                font-size: 14px;
            }
        """)

    def mousePressEvent(self, event):
        if event.modifiers() & Qt.ShiftModifier:
            self._is_all_expanded = True
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.modifiers() & Qt.ShiftModifier:
            self._is_all_expanded = False
        super().mouseReleaseEvent(event)



if __name__ == "__main__":
    stage = Usd.Stage.Open("/path")
    
    app = QtWidgets.QApplication(sys.argv)
    
    root = Usd.PrimRange(stage.GetPseudoRoot())
    viewer = PrimTreeView(prim_range=root)
    
    viewer.setMinimumWidth(750)
    viewer.show()
    
    sys.exit(app.exec_())
