from pymavlink.dialects.v20 import common

m = common.MAVLink_named_value_float_message
print("crc", m.crc_extra)
print("fieldnames", m.fieldnames)
print("ordered_fieldnames", getattr(m, "ordered_fieldnames", None))
print("formats", getattr(m, "formats", None))
