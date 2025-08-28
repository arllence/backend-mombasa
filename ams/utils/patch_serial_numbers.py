from shared_fxns import get_serial_number
from ams.models import Asset

def patchSerialNumber():
    assets = Asset.objects.all()
    for asset in assets:
        serial_no = get_serial_number(asset.properties)
        print("SERIAL NO: ", serial_no, "ASSET NO: ", asset.asset_no)
        asset.serial_no = serial_no
        asset.save()

