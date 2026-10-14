"""Offline, rule-based diagnosis for common SAP / OData / UI5 errors.

Used when no LLM key is configured, or when the LLM call fails, so
LogSense always returns a useful answer.
"""
import re
from dataclasses import dataclass, field


@dataclass
class Rule:
    pattern: str
    severity: str
    summary: str
    likely_cause: str
    fix_steps: list = field(default_factory=list)
    where_to_look: str = ""

    def matches(self, text: str) -> bool:
        return re.search(self.pattern, text, re.IGNORECASE) is not None


RULES = [
    Rule(
        pattern=r"No property '[^']+' exists|property .* (does not exist|not found)",
        severity="Medium",
        summary="The OData request references a property that is not defined in the entity type.",
        likely_cause="A $filter, $select, $orderby or binding path uses a field name that does not exist "
                     "in the service metadata (typo, wrong entity, or a field removed from the CDS view / SEGW model).",
        fix_steps=[
            "Open <service>/$metadata and check the exact property names of the entity type.",
            "Correct the Filter / sorter / binding path in the UI5 controller or view.",
            "If the field should exist, add it to the CDS view or SEGW entity and regenerate the service.",
        ],
        where_to_look="Service $metadata; /IWFND/ERROR_LOG on the Gateway hub for the failing request.",
    ),
    Rule(
        pattern=r"Resource not found for (the )?segment|Resource not found|HTTP 404",
        severity="Medium",
        summary="The OData service could not find the requested entity set or key.",
        likely_cause="The entity set name is wrong, the key value does not exist, or the service is not "
                     "registered / activated on the Gateway.",
        fix_steps=[
            "Check the entity set name against $metadata (names are case-sensitive).",
            "Verify the key value exists, e.g. read the entity set without a key first.",
            "Confirm the service is registered and active in /IWFND/MAINT_SERVICE.",
        ],
        where_to_look="/IWFND/MAINT_SERVICE, /IWFND/ERROR_LOG, browser Network tab.",
    ),
    Rule(
        pattern=r"CSRF token validation failed|x-csrf-token",
        severity="Medium",
        summary="A modifying OData request was rejected because the CSRF token was missing or expired.",
        likely_cause="POST/PUT/DELETE was sent without first fetching an X-CSRF-Token, or the session expired.",
        fix_steps=[
            "Let the UI5 ODataModel handle tokens (tokenHandling is on by default) instead of raw AJAX calls.",
            "If calling manually, send a GET with 'X-CSRF-Token: Fetch' first and reuse the returned token.",
            "Check that cookies/session are preserved through the proxy or destination.",
        ],
        where_to_look="Browser Network tab (request/response headers), /IWFND/ERROR_LOG.",
    ),
    Rule(
        pattern=r"HTTP 40[13]\b|not authori[sz]ed|No authorization|Forbidden",
        severity="High",
        summary="The user is not authenticated or lacks the authorization for this service or data.",
        likely_cause="Missing role / authorization object, expired login, or destination credentials not set.",
        fix_steps=[
            "Run transaction SU53 right after the failure to see the failed authorization check.",
            "Ask the security team to add the missing authorization to the user's role (PFCG).",
            "On BTP, verify the destination's authentication and the user's role collections.",
        ],
        where_to_look="SU53, PFCG, /IWFND/ERROR_LOG; BTP cockpit destinations and role collections.",
    ),
    Rule(
        pattern=r"CX_SY_ZERODIVIDE|COMPUTE_INT_ZERODIVIDE",
        severity="High",
        summary="ABAP runtime error: division by zero.",
        likely_cause="A calculation divides by a field or variable that is zero for some records.",
        fix_steps=[
            "Open the dump in ST22 and go to the source line shown under 'Source Code Extract'.",
            "Guard the division with IF lv_divisor <> 0, or handle CX_SY_ZERODIVIDE in TRY...CATCH.",
            "Check which input data produced the zero value.",
        ],
        where_to_look="ST22 (short dump), the ABAP source line in SE80 / ADT.",
    ),
    Rule(
        pattern=r"CX_SY_ITAB_LINE_NOT_FOUND|ITAB_LINE_NOT_FOUND",
        severity="High",
        summary="ABAP runtime error: an internal table line was accessed with a table expression but does not exist.",
        likely_cause="Code like lt_tab[ key = value ] was used without checking that the line exists.",
        fix_steps=[
            "Use line_exists( ) before the table expression, or use VALUE #( lt_tab[ ... ] OPTIONAL ).",
            "Alternatively wrap it in TRY...CATCH cx_sy_itab_line_not_found.",
            "Check why the expected record is missing in the data.",
        ],
        where_to_look="ST22 dump details and the source position in ADT / SE80.",
    ),
    Rule(
        pattern=r"CX_SY_REF_IS_INITIAL|OBJECTS_OBJREF_NOT_ASSIGNED|NULL object reference",
        severity="High",
        summary="ABAP runtime error: a method was called on an object reference that was never created.",
        likely_cause="An object was used before NEW / CREATE OBJECT, or a factory method returned an initial reference.",
        fix_steps=[
            "Find the reference variable in the ST22 source extract.",
            "Ensure it is instantiated before use, or check IS BOUND before calling methods.",
        ],
        where_to_look="ST22, debugger (set a breakpoint before the failing line).",
    ),
    Rule(
        pattern=r"CX_SY_CONVERSION_NO_NUMBER|CONVT_NO_NUMBER",
        severity="Medium",
        summary="ABAP runtime error: a text value could not be converted to a number.",
        likely_cause="Input data contains non-numeric characters where a number is expected.",
        fix_steps=[
            "Validate or clean the input before conversion.",
            "Catch CX_SY_CONVERSION_NO_NUMBER and return a meaningful message to the caller.",
        ],
        where_to_look="ST22, the source data feeding the conversion.",
    ),
    Rule(
        pattern=r"TIME_OUT|timed? ?out|HTTP 504",
        severity="High",
        summary="The request or ABAP program exceeded the allowed runtime.",
        likely_cause="An expensive database selection (missing index or filter), large result set, or slow backend call.",
        fix_steps=[
            "Add $top / $filter / paging so the service does not read everything at once.",
            "Analyse the SELECT with ST05 (SQL trace) and check indexes.",
            "Move heavy work to background processing if it cannot be optimised.",
        ],
        where_to_look="ST22, ST05 (SQL trace), SAT (runtime analysis), /IWFND/ERROR_LOG.",
    ),
    Rule(
        pattern=r"CORS|Cross-Origin|Access-Control-Allow-Origin",
        severity="Medium",
        summary="The browser blocked the request because of the cross-origin (CORS) policy.",
        likely_cause="The UI5 app calls the OData service directly on another origin without a proxy or destination.",
        fix_steps=[
            "Route the call through the UI5 tooling proxy (ui5.yaml) during development.",
            "On BTP, use a destination and the approuter / HTML5 repository instead of a direct URL.",
        ],
        where_to_look="Browser console and Network tab; ui5.yaml / xs-app.json routes.",
    ),
    Rule(
        pattern=r"HTTP 500|Internal Server Error|In the context of Data Services an unknown internal server error",
        severity="High",
        summary="The OData backend raised an unhandled error while processing the request.",
        likely_cause="An exception inside the DPC_EXT / RAP implementation or a short dump in the backend.",
        fix_steps=[
            "Look up the request in /IWFND/ERROR_LOG (hub) and /IWBEP/ERROR_LOG (backend).",
            "Check ST22 for a short dump at the same timestamp.",
            "Reproduce in /IWFND/GW_CLIENT and debug the service implementation.",
        ],
        where_to_look="/IWFND/ERROR_LOG, /IWBEP/ERROR_LOG, ST22, /IWFND/GW_CLIENT.",
    ),
]

GENERIC = Rule(
    pattern=r".*",
    severity="Low",
    summary="No known pattern matched this log.",
    likely_cause="The error is not one of the common cases recognised offline. "
                 "Configure GROQ_API_KEY for a full AI analysis.",
    fix_steps=[
        "Find the first error line in the log (the root cause is usually the earliest exception).",
        "Check the exact message text against the service metadata or ABAP source.",
        "Reproduce the request in isolation (Gateway client or browser) to narrow it down.",
    ],
    where_to_look="ST22 for dumps, /IWFND/ERROR_LOG for OData, SM21 system log, browser console for UI5.",
)


def diagnose(log: str) -> dict:
    for rule in RULES:
        if rule.matches(log):
            break
    else:
        rule = GENERIC
    return {
        "severity": rule.severity,
        "summary": rule.summary,
        "likely_cause": rule.likely_cause,
        "fix_steps": list(rule.fix_steps),
        "where_to_look": rule.where_to_look,
        "source": "offline SAP rule base",
    }
