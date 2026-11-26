"""
tif_meta.py
===========
Keeps the metadata of the image of a folder (the 'base' tif) in every tif the pipeline writes:
ImageJ 'Info' text (Zeiss acquisition parameters, read later by optics.py), pixel size, z step, unit.
Without it a derived file (crop, composite...) loses the optical parameters and the PSF cannot be computed.
Only needs tifffile.
"""
import tifffile

XML_BEGIN, XML_END = "#CZI_XML_BEGIN#", "#CZI_XML_END#"


def czi_info(xml_text):
    """Info text for a tif converted from a czi: the whole Zen XML, read back by optics.py."""
    return f"{XML_BEGIN}\n{xml_text}\n{XML_END}\n"


def parent_kwargs(base_path, axes=None, channels=None, **extra_metadata):
    """
    Keyword arguments for tifffile.imwrite(..., imagej=True, **kwargs) that carry the metadata of base_path.
    channels: indices (in the base file) of the channels kept, when the new file has only some of them;
              written in the Info so that optics.py finds the right channel again.
    """
    meta, kw = {}, {}
    try:
        with tifffile.TiffFile(base_path) as tf:
            ij = dict(tf.imagej_metadata or {})
            page = tf.pages[0]
            xr, yr = page.tags.get("XResolution"), page.tags.get("YResolution")
            if xr is not None and yr is not None:
                kw["resolution"] = (xr.value[0] / xr.value[1], yr.value[0] / yr.value[1])
    except Exception:
        ij = {}
    for key in ("unit", "spacing", "Info"):
        if ij.get(key) not in (None, ""):
            meta[key] = ij[key]
    if meta.get("unit") == "\\u00B5m":
        meta["unit"] = "um"
    if channels is not None and meta.get("Info") is not None:
        meta["Info"] = str(meta["Info"]).rstrip("\n") + "\n Parent channels = " + ",".join(str(int(c)) for c in channels) + "\n"
    if axes:
        meta["axes"] = axes
    meta.update({k: v for k, v in extra_metadata.items() if v is not None})
    kw["metadata"] = meta
    return kw


def write_like(path, data, base_path, axes=None, channels=None, **extra_metadata):
    """tifffile.imwrite with the metadata of the base image (ImageJ format)."""
    import numpy as np
    data = np.asarray(data)
    if data.dtype not in (np.uint8, np.uint16, np.float32):            # ImageJ format limits
        if data.dtype.kind in "iub" and data.size and 0 <= data.min() and data.max() < 65536:
            data = data.astype(np.uint16)
        else:
            data = data.astype(np.float32)
    tifffile.imwrite(path, data, imagej=True, **parent_kwargs(base_path, axes, channels, **extra_metadata))


def convert_czi(czi_path, out_tif):
    """
    Converts a Zeiss czi into a (Z, C, Y, X) ImageJ tif: pixel size and z step in the metadata, and the whole Zen
    XML in 'Info' (read back by optics.py). Needs czifile and aicspylibczi (environment 'spots_analysis').
    """
    import xml.etree.ElementTree as ET
    import numpy as np
    from czifile import CziFile
    from aicspylibczi import CziFile as AicsCzi
    meta = AicsCzi(czi_path).meta
    zen_info = czi_info(ET.tostring(meta, encoding="unicode"))
    scaling_x = float(meta.find(".//ScalingX").text) * 1e6      # m -> um
    scaling_y = float(meta.find(".//ScalingY").text) * 1e6
    scaling_z = float(meta.find(".//ScalingZ").text) * 1e6
    img = np.transpose(np.squeeze(CziFile(czi_path).asarray()), (1, 0, 2, 3))
    tifffile.imwrite(out_tif, img, imagej=True, resolution=(1 / scaling_x, 1 / scaling_y),
                     metadata={"axes": "ZCYX", "spacing": scaling_z, "unit": "um", "Info": zen_info})
    return out_tif


if __name__ == "__main__":                       # python tif_meta.py convert <file.czi> <out.tif>
    import sys
    if len(sys.argv) == 4 and sys.argv[1] == "convert":
        convert_czi(sys.argv[2], sys.argv[3])
        print("converted")
    else:
        sys.exit("usage: python tif_meta.py convert <file.czi> <out.tif>")
