"""
Vendor / dataset column-mapping configuration.

To add a vendor (Ericsson, ZTE, ...): copy the "huawei" entry, change
`title`/`detect`/`fields` to match that vendor's export column names,
and register it under VENDOR_PROFILES. Nothing else in the backend
needs to change.

`detect`  -- which normalized headers must be present to recognise a
             CSV as this dataset. `required` must ALL be present;
             `any_of` needs at least one match (used when a value can
             live under either of two legacy column names).
`fields`  -- canonical field name -> ordered list of normalized header
             aliases to try (first non-empty value wins). This also
             transparently handles vendor exports that duplicate a
             column under a "friendly" name and a short code (we saw
             this in the DEVIP/VLAN samples), since both aliases are
             just tried in order.
`ne_from_split` -- for GSM/UMTS, the real NE name lives inside another
             column as "ALIAS@NE" (BSC/RNC-configured name @ physical
             NE). Set to the canonical field holding that value.
`bucket`  -- which Store bucket / ingestion routine this dataset feeds
             (devip/vlan/s1/lte/nr/gsm/umts/neReport). Defaults to the
             dataset's own key if omitted, which is why Huawei's
             entries (whose keys already match a bucket 1:1) don't
             need to set it. A vendor can have *several* dataset kinds
             feed the same bucket -- e.g. Ericsson's "neInventory" and
             "neAudit" both set bucket="neReport" and get merged
             together (see store.merge_ne_report) instead of one
             clobbering the other.
"""

VENDOR_PROFILES = {
    "huawei": {
        "label": "Huawei",
        "datasets": {
            "devip": {
                "title": "DEVIP",
                "skip_file_pattern": r"bfkt",
                "detect": {"required": ["cabinetno", "nename"], "any_of": ["ipaddress", "ip"]},
                "fields": {
                    "ne": ["nename"],
                    "ip": ["ipaddress", "ip"],
                    "mask": ["mask"],
                    "userLabel": ["userlabel"],
                    "portType": ["porttype"],
                    "portNo": ["portno"],
                    "vrfIndex": ["vrfindex", "vrfidx"],
                    "cabinet": ["cabinetno"],
                    "subrack": ["subrackno"],
                    "slot": ["slotno"],
                    "subboard": ["subboardtype"],
                    "ctrlMode": ["controlmode", "ctrlmode"],
                    "borrowIfip": ["borrowifip"],
                },
            },
            "vlan": {
                "title": "VLAN",
                "skip_file_pattern": r"bfkt",
                "detect": {"required": ["vlanid", "nexthopip", "nename"]},
                "fields": {
                    "ne": ["nename"],
                    "vrfIndex": ["vrfindex", "vrfidx"],
                    "nextHopIp": ["nexthopip"],
                    "mask": ["mask"],
                    "vlanMode": ["vlanmode"],
                    "vlanId": ["vlanid"],
                    "setPrio": ["setvlanpriority", "setprio"],
                    "vlanPrio": ["vlanpriority", "vlanprio"],
                    "vlanGroupNo": ["vlangroupno"],
                },
            },
            "s1": {
                "title": "LTE S1",
                "detect": {"required": ["s1interfaceid", "sctplinkno"]},
                "fields": {
                    "ne": ["nename"],
                    "connStatus": ["enodebconnectionstatus"],
                    "s1IfId": ["s1interfaceid"],
                    "s1IfStatus": ["s1interfacestatus"],
                    "sctpLinkNo": ["sctplinkno"],
                    "sctpLinkStatus": ["sctplinkstatus"],
                    "cause": ["causeofs1interfaceexception"],
                    "localIp": ["localipaddressofsctp"],
                    "localPort": ["localportofsctp"],
                    "peerIp": ["peeripaddressofsctp"],
                    "peerPort": ["peerportofsctp"],
                    "sctpBlock": ["sctpblockidentity"],
                },
            },
            "lte": {
                "title": "LTE",
                "detect": {"required": ["ltenename"]},
                "fields": {
                    "controller": ["nename"],
                    "subarea": ["subarea"],
                    "rat": ["rat"],
                    "enbId": ["enodebid"],
                    "ne": ["ltenename"],
                    "enbFunction": ["enodebfunctionname"],
                    "connStatus": ["neconnectionstatus"],
                    "cellId": ["cellid"],
                    "cellName": ["cellname"],
                    "localCellId": ["localcellid"],
                    "tac": ["tac"],
                    "band": ["frequencyband"],
                    "phyCellId": ["physicalcellid"],
                    "earfcn": ["dlearfcn"],
                    "adminStatus": ["administrativestatus"],
                    "activationStatus": ["activationstatus"],
                    "operStatus": ["operatingstatus"],
                    "availStatus": ["availabilitystatus"],
                },
            },
            "nr": {
                "title": "NR",
                "detect": {"required": ["nrnename"]},
                "fields": {
                    "controller": ["nename"],
                    "subarea": ["subarea"],
                    "rat": ["rat"],
                    "gnbId": ["gnodebid"],
                    "ne": ["nrnename"],
                    "gnbFunction": ["gnodebfunctionname"],
                    "connStatus": ["neconnectionstatus"],
                    "cellId": ["nrcellid", "cellid"],
                    "cellName": ["cellname"],
                    "tac": ["tac"],
                    "band": ["frequencyband"],
                    "phyCellId": ["physicalcellid"],
                    "earfcn": ["dlnarfcn"],
                    "adminStatus": ["administrativestatus"],
                    "activationStatus": ["activationstatus"],
                    "operStatus": ["operatingstatus"],
                    "availStatus": ["availabilitystatus"],
                },
            },
            "gsm": {
                "title": "GSM",
                "detect": {"required": ["sitename", "bcchno"]},
                "ne_from_split": "siteName",
                "fields": {
                    "bsc": ["nename"],
                    "siteIndex": ["siteindex"],
                    "siteName": ["sitename"],
                    "cellIndex": ["cellindex"],
                    "cellName": ["cellname"],
                    "activityStatus": ["activitystatus"],
                    "ci": ["ci"],
                    "basei": ["basei"],
                    "ni": ["ni"],
                    "bcchno": ["bcchno"],
                    "band": ["freqseg"],
                    "blkStatus": ["blkstatus"],
                    "hopHsn": ["hophsn"],
                    "hopTsc": ["hoptsc"],
                    "hopIndex": ["hopindex"],
                    "lac": ["lac"],
                    "rac": ["rac"],
                },
            },
            "umts": {
                "title": "UMTS",
                "detect": {"required": ["nodebname"]},
                "ne_from_split": "nodebName",
                "fields": {
                    "rnc": ["nename"],
                    "nodebId": ["nodebid"],
                    "nodebName": ["nodebname"],
                    "cellId": ["cellid"],
                    "cellName": ["cellname"],
                    "connStatus": ["rncconnectionstatus"],
                    "activityStatus": ["activitystatus"],
                    "blkStatus": ["blkstatus"],
                    "lac": ["lac"],
                    "sac": ["sac"],
                    "rac": ["rac"],
                    "ulFreq": ["ulfreq"],
                    "dlFreq": ["dlfreq"],
                    "maxPower": ["maxpower"],
                    "cbsState": ["cellcbsstate"],
                    "mbmsState": ["cellmbmsstate"],
                    "hsdpaOp": ["hsdpaopstate"],
                    "hsupaOp": ["hsupaopstate"],
                },
            },
            "neReport": {
                "title": "NE Report",
                "detect": {"required": ["netype"], "any_of": ["ipaddress1", "version"]},
                "fields": {
                    "ne": ["nename"],
                    "neType": ["netype"],
                    "ip1": ["ipaddress1"],
                    "ip2": ["ipaddress2"],
                    "version": ["version"],
                    "medPartition": ["medpartition"],
                    "subareaIp": ["subareaip"],
                    "timeZone": ["timezone"],
                    "physLocation": ["physicallocation"],
                    "vendor": ["vendor"],
                    "description": ["description"],
                    "district": ["district"],
                    "longitude": ["longitude"],
                    "latitude": ["latitude"],
                    "capacity": ["capacity"],
                    "region": ["region"],
                    "maintStatus": ["maintenancestatus"],
                    "neConnStatus": ["neconnectionstatus"],
                    "baseStationRat": ["basestationrat"],
                    "baseStationId": ["basestationid"],
                    "baseStationRnc": ["basestationrnc"],
                    "homeSubnet": ["homesubnet"],
                    "productType": ["producttype"],
                    "neMaintMode": ["nemaintenancemode"],
                    "creationTime": ["creationtime"],
                },
            },
        },
    },
    "ericsson": {
        "label": "Ericsson",
        "datasets": {
            # `cmedit get * NetworkElement.(...)` CLI dumps (ENM-FDD*.txt,
            # ENM-TDD*.txt, ENM*A.txt, ...). One row per NE.
            "neInventory": {
                "title": "ENM NE Inventory",
                "bucket": "neReport",
                "detect": {"required": ["nodeid", "managementstate", "neproductversion", "netype", "ossprefix", "radioaccesstechnology"]},
                "fields": {
                    "ne": ["nodeid"],
                    "neType": ["netype"],
                    "version": ["neproductversion"],
                    "neConnStatus": ["managementstate"],
                    "baseStationRat": ["radioaccesstechnology"],
                    "productType": ["release"],
                    "physLocation": ["ossprefix"],
                },
            },
            # A second `cmedit get` block further down the same ENM*.txt
            # files: legacy 3G RBS (NodeB) inventory, keyed by the
            # controlling RNC. Must be checked before "neInventoryErbs"
            # below since its header is a superset of that one's.
            "neInventoryRbs": {
                "title": "ENM RBS Inventory",
                "bucket": "neReport",
                "detect": {"required": ["nodeid", "controllingrnc", "managementstate", "neproductversion", "networkfunctions"]},
                "fields": {
                    "ne": ["nodeid"],
                    "neType": ["netype"],
                    "version": ["neproductversion"],
                    "neConnStatus": ["managementstate"],
                    "baseStationRnc": ["controllingrnc"],
                    "baseStationRat": ["technologydomain"],
                },
            },
            # Same file, a third `cmedit get` block: legacy 4G ERBS
            # (eNodeB) inventory -- no controlling-RNC column, which is
            # what distinguishes it from the RBS block above.
            "neInventoryErbs": {
                "title": "ENM ERBS Inventory",
                "bucket": "neReport",
                "detect": {"required": ["nodeid", "managementstate", "neproductversion", "networkfunctions", "nodemodelidentity", "technologydomain"]},
                "fields": {
                    "ne": ["nodeid"],
                    "neType": ["netype"],
                    "version": ["neproductversion"],
                    "neConnStatus": ["managementstate"],
                    "baseStationRat": ["technologydomain"],
                },
            },
            # "Network Dump Audit" sheet inside NetworkDumpAuditReport*.xlsx.
            # Same NEs as the inventory dump, richer detail (IP, sync
            # status, base station IDs) -- merged into the same neReport
            # rather than appended, since it's keyed by 'nodeid' too.
            "neAudit": {
                "title": "ENM Network Dump Audit",
                "bucket": "neReport",
                "detect": {"required": ["nodeid", "ipaddress", "syncstatus", "managementstatus"]},
                "fields": {
                    "ne": ["nodeid"],
                    "neType": ["netype"],
                    "version": ["neprocustionversion", "neproductversion"],
                    "neConnStatus": ["managementstatus"],
                    "baseStationRat": ["radioaccesstechnology"],
                    "productType": ["release"],
                    "ip1": ["ipaddress"],
                    "maintStatus": ["syncstatus"],
                    "baseStationId": ["enbid", "gnbid", "rbsid"],
                    "baseStationRnc": ["controllingrnc"],
                },
            },
            # "Disabled Mme Status Report" sheet inside MmeStatusReport*.xlsx
            # -- Ericsson's equivalent of the LTE S1/MME transport link
            # status (Huawei's "s1" dataset).
            "s1": {
                "title": "MME Status",
                "detect": {"required": ["nodeid", "termpointtommeid", "operationalstate", "usedipaddress"]},
                "fields": {
                    "ne": ["nodeid"],
                    "s1IfId": ["termpointtommeid"],
                    "connStatus": ["operationalstate"],
                    "peerIp": ["ipaddress1"],
                    "localIp": ["usedipaddress"],
                },
            },
            # "2G" sheet inside NetworkDumpAuditReport*.xlsx -- BSC/site/
            # sector inventory. Note: RSITE is its own namespace and isn't
            # guaranteed to line up with the RadioNode NodeIds from the
            # ENM inventory dump above, so a GSM site may show up under a
            # name that doesn't match its 4G/5G NodeId at the same
            # physical location.
            "gsm": {
                "title": "2G Site Inventory",
                "detect": {"required": ["bsc", "mo", "sector", "rsite"]},
                "fields": {
                    "ne": ["rsite"],
                    "bsc": ["bsc"],
                    "cellName": ["mo"],
                    "ci": ["sector"],
                    "model": ["model"],
                    "swVersion": ["swverdld"],
                },
            },
            # "NRCellDU" -- from either the raw ENM*.txt `cmedit get *
            # NRCellDU...` blocks or the consolidated "NRCellDU" sheet
            # in Network Cell Status Output*.xlsx (same core columns in
            # both, so one mapping covers either source). Upload ONE of
            # the two per report run -- uploading both double-counts
            # every cell.
            "nrCellDU": {
                "title": "NR Cell (NRCellDU)",
                "bucket": "nr",
                "detect": {"required": ["nodeid", "gnbdufunctionid", "nrcellduid", "administrativestate", "operationalstate"]},
                "fields": {
                    "ne": ["nodeid"],
                    "gnbId": ["gnbdufunctionid"],
                    "cellId": ["nrcellduid"],
                    "cellName": ["nrcellduid"],
                    "adminStatus": ["administrativestate"],
                    "operStatus": ["operationalstate"],
                },
            },
            # "EUtranCellFDD" -- txt block or xlsx sheet, same idea.
            "eutranCellFdd": {
                "title": "LTE Cell (EUtranCellFDD)",
                "bucket": "lte",
                "detect": {"required": ["nodeid", "enodebfunctionid", "eutrancellfddid", "administrativestate", "operationalstate"]},
                "fields": {
                    "ne": ["nodeid"],
                    "enbId": ["enodebfunctionid"],
                    "cellId": ["eutrancellfddid"],
                    "cellName": ["eutrancellfddid"],
                    "adminStatus": ["administrativestate"],
                    "operStatus": ["operationalstate"],
                },
            },
            # "EUtranCellTDD" -- txt block or xlsx sheet, same idea.
            "eutranCellTdd": {
                "title": "LTE Cell (EUtranCellTDD)",
                "bucket": "lte",
                "detect": {"required": ["nodeid", "enodebfunctionid", "eutrancelltddid", "administrativestate", "operationalstate"]},
                "fields": {
                    "ne": ["nodeid"],
                    "enbId": ["enodebfunctionid"],
                    "cellId": ["eutrancelltddid"],
                    "cellName": ["eutrancelltddid"],
                    "adminStatus": ["administrativestate"],
                    "operStatus": ["operationalstate"],
                },
            },
            # "UtranCell" from the xlsx sheet -- richer: includes the
            # controlling RNC's friendly name and the Iub link's own
            # admin/oper state alongside the cell's.
            "utranCellXlsx": {
                "title": "UMTS Cell (UtranCell)",
                "bucket": "umts",
                "detect": {"required": ["nodeid", "rncfunctionid", "utrancellid", "celladministrativestate", "celloperationalstate", "rnc"]},
                "fields": {
                    "ne": ["nodeid"],
                    "rnc": ["rnc"],
                    "nodebId": ["rncfunctionid"],
                    "cellId": ["utrancellid"],
                    "cellName": ["utrancellid"],
                    "blkStatus": ["celladministrativestate"],
                    "activityStatus": ["celloperationalstate"],
                },
            },
            # "Utrancell" from the raw ENM*.txt block -- no RNC friendly
            # name here (that's only in the xlsx export); has an Iub
            # link reference instead, which we don't currently join.
            "utranCellTxt": {
                "title": "UMTS Cell (UtranCell, txt)",
                "bucket": "umts",
                "detect": {"required": ["nodeid", "rncfunctionid", "utrancellid", "administrativestate", "operationalstate", "iublinkref"]},
                "fields": {
                    "ne": ["nodeid"],
                    "nodebId": ["rncfunctionid"],
                    "cellId": ["utrancellid"],
                    "cellName": ["utrancellid"],
                    "blkStatus": ["administrativestate"],
                    "activityStatus": ["operationalstate"],
                },
            },
            # TODO: "IubLink" blocks (Iub transport admin/oper state,
            # keyed by RncFunctionId+IubLinkId) aren't joined into the
            # UMTS cell records yet -- would need a two-pass merge like
            # neReport's, keyed by RncFunctionId rather than NE name.
            #
            # TODO: no per-cell LTE/NR/UMTS detail (TAC, PCI, EARFCN,
            # admin/oper status) was present in this particular report
            # bundle -- only NE-level inventory and BSC/site-level GSM
            # data. When a cell-level Ericsson export is available,
            # add "lte"/"nr"/"umts" entries here the same way the
            # Huawei profile does.
        },
    },
    # TODO: mirror the "huawei" profile above with real ZTE export headers.
    "zte": {"label": "ZTE", "datasets": {}},
}


def normalize(s) -> str:
    """Lowercase, strip everything but alphanumerics -- makes header
    matching resilient to whitespace/casing/punctuation differences
    between exports."""
    if s is None:
        return ""
    return "".join(ch for ch in str(s).lower() if ch.isalnum())
