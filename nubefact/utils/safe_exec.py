from frappe.utils.safe_exec import NamespaceDict

from nubefact.utils import make_request


def safe_exec_globals(out):

    return {"nubefact": NamespaceDict({"make_request": make_request})}
