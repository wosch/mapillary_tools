import sys
import json
import datetime
import hashlib
import base64
import uuid
from lib.geo import normalize_bearing
from lib.exif import EXIF, verify_exif
from lib.pexif import JpegFile, Rational


def create_mapillary_description(filename, username, email,
                                 upload_hash, sequence_uuid,
                                 interpolated_heading=None,
                                 orientation=1,
                                 verbose=False):
    """
    Check that image file has the required EXIF fields.

    Incompatible files will be ignored server side.
    """
    # read exif
    exif = EXIF(filename)

    if not verify_exif(filename):
        return False

    # Write the mapillary tag
    mapillary_description = {}
    mapillary_description["MAPLongitude"], mapillary_description["MAPLatitude"] = exif.extract_lon_lat()

    #required date format: 2015_01_14_09_37_01_000
    mapillary_description["MAPCaptureTime"] = datetime.datetime.strftime(exif.extract_capture_time(), "%Y_%m_%d_%H_%M_%S_%f")[:-3]
    mapillary_description["MAPOrientation"] = exif.extract_orientation()

    heading = exif.extract_direction()
    if heading is None:
        heading = 0.0
    heading = normalize_bearing(interpolated_heading) if interpolated_heading is not None else normalize_bearing(heading)

    mapillary_description["MAPCompassHeading"] = {"TrueHeading": heading,
                                                  "MagneticHeading": heading}
    mapillary_description["MAPSettingsUploadHash"] = upload_hash
    mapillary_description["MAPSettingsEmail"] = email
    mapillary_description["MAPSettingsUsername"] = username
    settings_upload_hash = hashlib.sha256("%s%s%s" % (upload_hash, email, base64.b64encode(filename))).hexdigest()
    mapillary_description['MAPSettingsUploadHash'] = settings_upload_hash
    mapillary_description['MAPPhotoUUID'] = str(uuid.uuid4())
    mapillary_description['MAPSequenceUUID'] = str(sequence_uuid)
    mapillary_description['MAPDeviceModel'] = exif.extract_model()
    mapillary_description['MAPDeviceMake'] = exif.extract_make()

    # write to file
    json_desc = json.dumps(mapillary_description)
    if verbose:
        print "tag: {0}".format(json_desc)
    metadata = ExifEdit(filename)
    metadata.add_image_description(mapillary_description)
    metadata.add_orientation(orientation)
    metadata.add_direction(heading)
    metadata.write()

class ExifEdit(object):

    def __init__(self, filename):
        """Initialize the object"""
        self.filename = filename
        self.ef = None
        try:
            if (type(filename) is str) or (type(filename) is unicode):
                self.ef = JpegFile.fromFile(filename)
            else:
                filename.seek(0)
                self.ef = JpegFile.fromString(filename.getvalue())
        except IOError:
            etype, value, traceback = sys.exc_info()
            print >> sys.stderr, "Error opening file:", value
        except JpegFile.InvalidFile:
            etype, value, traceback = sys.exc_info()
            print >> sys.stderr, "Error opening file:", value

    def add_image_description(self, dict):
        """Add a dict to image description."""
        if self.ef is not None:
            self.ef.exif.primary.ImageDescription = json.dumps(dict)

    def add_orientation(self, orientation):
        """Add image orientation to image."""
        self.ef.exif.primary.Orientation = [orientation]

    def add_date_time_original(self, date_time):
        """Add date time original."""
        self.ef.exif.primary.ExtendedEXIF.DateTimeOriginal = date_time.strftime('%Y:%m:%d %H:%M:%S')

    def add_lat_lon(self, lat, lon):
        """Add lat, lon to gps (lat, lon in float)."""
        self.ef.set_geo(float(lat), float(lon))

    def add_dop(self, dop, perc=100):
        """Add GPSDOP (float)."""
        self.ef.exif.primary.GPS.GPSDOP = [Rational(abs(dop * perc), perc)]

    def add_altitude(self, altitude, precision=100):
        """Add altitude (pre is the precision)."""
        ref = '\x00' if altitude > 0 else '\x01'
        self.ef.exif.primary.GPS.GPSAltitude = [Rational(abs(altitude * precision), precision)]
        self.ef.exif.primary.GPS.GPSAltitudeRef = [ref]

    def add_direction(self, direction, ref="T", precision=100):
        """Add image direction."""
        self.ef.exif.primary.GPS.GPSImgDirection = [Rational(abs(direction * precision), precision)]
        self.ef.exif.primary.GPS.GPSImgDirectionRef = ref

    def write(self, filename=None):
        """Save exif data to file."""
        try:
            if filename is None:
                filename = self.filename
            self.ef.writeFile(filename)
        except IOError:
            type, value, traceback = sys.exc_info()
            print >> sys.stderr, "Error saving file:", value

    def write_to_string(self):
        """Save exif data to StringIO object."""
        return self.ef.writeString()

    def write_to_file_object(self):
        """Save exif data to file object."""
        return self.ef.writeFd()
