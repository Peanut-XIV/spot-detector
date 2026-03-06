from PySide6.QtCore import Qt


def ItemDataRole_to_string(role: Qt.ItemDataRole) -> str:
    Role = Qt.ItemDataRole
    role_names = {
        Role.DisplayRole: "Display",
        Role.DecorationRole: "Decoration",
        Role.EditRole: "Edit",
        Role.ToolTipRole: "ToolTip",
        Role.StatusTipRole: "StatusTip",
        Role.WhatsThisRole: "WhatsThis",
        Role.FontRole: "Font",
        Role.TextAlignmentRole: "TextAlignment",
        Role.BackgroundRole: "Background",
        Role.ForegroundRole: "Foreground",
        Role.CheckStateRole: "CheckState",
        Role.AccessibleTextRole: "AccessibleText",
        Role.AccessibleDescriptionRole: "AccessibleDescription",
        Role.SizeHintRole: "SizeHint",
        Role.InitialSortOrderRole: "InitialSortOrder",
        Role.DisplayPropertyRole: "DisplayProperty",
        Role.DecorationPropertyRole: "DecorationProperty",
        Role.ToolTipPropertyRole: "ToolTipProperty",
        Role.StatusTipPropertyRole: "StatusTipProperty",
        Role.WhatsThisPropertyRole: "WhatsThisProperty",
    }

    if role in role_names.keys():
        return role_names[role]
    elif role >= Role.UserRole:
        return f"UserRole({role})"
    else:
        return f"UndefinedRole({role})"
