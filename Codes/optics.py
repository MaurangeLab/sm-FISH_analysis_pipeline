"""
optics.py - acquisition metadata, theoretical PSF and 3D Gaussian fit of a spot.
Used by Newmain.py (same folder). Nothing here needs a GPU or a conda environment.

1. read_acquisition(tif, channel)  : NA, immersion, wavelengths, pinhole, pixel size... read from the metadata
                                     that Zeiss Zen / Fiji / Bio-Formats write in an ImageJ tif ("Info" text).
2. psf_widths(acq)                 : widths (sigma, nm) of the theoretical confocal PSF: scalar Debye model
                                     (Born and Wolf) for the excitation and the detection, the detection being
                                     convolved with the pinhole; the widths are those of the Gaussians having
                                     the same full width at half maximum.
3. fit_spot(...)                   : 3D Gaussian fit of one spot (pixel-integrated model, background given).
"""
import re
import numpy as np

FWHM_TO_SIGMA = 1 / (2 * np.sqrt(2 * np.log(2)))


# ==============================================================================
# 1. METADATA
# ==============================================================================
# Every quantity: list of candidate keys of the Info text (first one found wins), the channel suffix ' #n' is
# tried first, then the key alone. factor converts the stored number to the unit in the field name.
_CHANNEL_FIELDS = {
    "excitation_nm": (["Information|Image|Channel|ExcitationWavelength", "Information|Image|Channel|Wavelength"], 1),
    "emission_nm": (["Information|Image|Channel|EmissionWavelength"], 1),
    "pinhole_au": (["Information|Image|Channel|PinholeSizeAiry"], 1),
    "pinhole_detector_um": (["Experiment|AcquisitionBlock|MultiTrackSetup|TrackSetup|Detector|PinholeDiameter"], 1e6),
    "gain": (["Information|Image|Channel|Gain"], 1),
}
_GLOBAL_FIELDS = {
    "na": (["Information|Instrument|Objective|LensNA"], 1),
    "refractive_index": (["Information|Image|RefractiveIndex"], 1),
    "magnification": (["Information|Instrument|Objective|NominalMagnification"], 1),
    "pixel_xy_nm": (["Experiment|AcquisitionBlock|AcquisitionModeSetup|ScalingX"], 1e9),
    "step_z_nm": (["Experiment|AcquisitionBlock|AcquisitionModeSetup|ScalingZ"], 1e9),
}
_TEXT_FIELDS = {"objective": "Information|Instrument|Objective|Manufacturer|Model",
                "immersion": "Information|Instrument|Objective|Immersion"}


def _info_text(tif_path):
    import tifffile
    try:
        with tifffile.TiffFile(tif_path) as tf:
            ij = tf.imagej_metadata or {}
            return ij.get("Info", "") or ""
    except Exception:
        return ""


def _values_from_xml(info):
    """The Zen XML kept in the Info (czi conversion) read as the 'Key = value' pairs the code below uses."""
    import xml.etree.ElementTree as ET
    xml = info.split("#CZI_XML_BEGIN#", 1)[1].split("#CZI_XML_END#", 1)[0].strip()
    values = {}
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return values

    def text(el):
        return (el.text or "").strip() if el is not None else ""

    def first(path):
        return text(root.find(path))

    for key, path in (("Information|Image|RefractiveIndex", ".//Information/Image/RefractiveIndex"),
                      ("Information|Instrument|Objective|LensNA", ".//Objective/LensNA"),
                      ("Information|Instrument|Objective|NominalMagnification", ".//Objective/NominalMagnification"),
                      ("Information|Image|RefractiveIndex", ".//Image/ObjectiveSettings/RefractiveIndex"),
                      ("Information|Instrument|Objective|Manufacturer|Model", ".//Objective/Manufacturer/Model"),
                      ("Information|Instrument|Objective|Immersion", ".//Objective/Immersion"),
                      ("Experiment|AcquisitionBlock|AcquisitionModeSetup|ScalingX", ".//AcquisitionModeSetup/ScalingX"),
                      ("Experiment|AcquisitionBlock|AcquisitionModeSetup|ScalingZ", ".//AcquisitionModeSetup/ScalingZ")):
        v = first(path)
        if v and key not in values:
            values[key] = v
    channels = [c for c in root.iter("Channel") if c.find("ExcitationWavelength") is not None or c.find("PinholeSizeAiry") is not None]
    for i, ch in enumerate(channels, 1):
        for tag in ("ExcitationWavelength", "Wavelength", "EmissionWavelength", "PinholeSizeAiry", "Gain"):
            v = text(ch.find(tag)) or (text(ch.find("DetectorSettings/Gain")) if tag == "Gain" else "")
            if v:
                values[f"Information|Image|Channel|{tag} #{i}"] = v
        rng = text(ch.find("DetectionWavelength/Ranges"))
        if rng:
            values[f"Information|Image|Channel|DetectionWavelength|Ranges #{i}"] = rng
    for i, det in enumerate(root.findall(".//TrackSetup/Detectors/Detector/PinholeDiameter")
                            or root.findall(".//TrackSetup/Detector/PinholeDiameter"), 1):
        if text(det):
            values[f"Experiment|AcquisitionBlock|MultiTrackSetup|TrackSetup|Detector|PinholeDiameter #{i}"] = text(det)
    return values


def read_acquisition(tif_path, channel):
    """
    Acquisition parameters of one channel (0-based). Missing values are None.
    The channel number of Zen is channel + 1 (' #1', ' #2'... in the key names).
    Returns a dict, with "source" = "metadata" or "none".
    """
    info = _info_text(tif_path)
    out = {k: None for k in list(_CHANNEL_FIELDS) + list(_GLOBAL_FIELDS) + list(_TEXT_FIELDS)}
    out["detection_range_nm"] = None
    out["source"] = "none"
    if not info:
        return out
    values = {}
    if "#CZI_XML_BEGIN#" in info:
        values = _values_from_xml(info)                       # base converted from a czi by the pipeline
    for line in ([] if values else info.splitlines()):
        if " = " in line:
            key, val = line.split(" = ", 1)
            values[key.strip()] = val.strip()
    # file that holds only some channels of its parent (a crop): its channel k is the parent's channel list[k]
    m = re.search(r"^\s*Parent channels = ([\d, ]+)$", info, re.M)
    parent = m.group(1) if m else None
    if parent:
        try:
            channel = [int(c) for c in parent.split(",")][channel]
        except (ValueError, IndexError):
            pass

    def number(keys, suffix):
        for key in keys:
            for k in ([f"{key} #{suffix}"] if suffix else []) + [key]:
                if k in values:
                    try:
                        return float(values[k].replace(",", "."))
                    except ValueError:
                        pass
        return None

    for name, (keys, factor) in _CHANNEL_FIELDS.items():
        v = number(keys, channel + 1)
        out[name] = None if v is None else v * factor
    for name, (keys, factor) in _GLOBAL_FIELDS.items():
        v = number(keys, None)
        out[name] = None if v is None else v * factor
    for name, key in _TEXT_FIELDS.items():
        out[name] = values.get(key)
    rng = values.get(f"Information|Image|Channel|DetectionWavelength|Ranges #{channel + 1}")
    if rng and re.match(r"^[\d.]+-[\d.]+$", rng):
        lo, hi = rng.split("-")
        out["detection_range_nm"] = (float(lo), float(hi))
    out["source"] = "metadata"
    return out


def merge_overrides(acq, overrides):
    """Values typed in the GUI replace the ones read from the image (empty / None = keep the metadata)."""
    out = dict(acq)
    for key, value in (overrides or {}).items():
        if value is None or str(value).strip() == "":
            continue
        try:
            out[key] = float(str(value).replace(",", "."))
        except ValueError:
            continue
        out["source"] = "metadata + user values" if acq.get("source") == "metadata" else "user values"
    return out


def missing_for_psf(acq, need_pinhole=False):
    """Parameters of the PSF that the image does not give (the pinhole only counts for a confocal calculation)."""
    needed = ["na", "refractive_index", "emission_nm", "excitation_nm"]
    missing = [k for k in needed if not acq.get(k)]
    if need_pinhole and not (acq.get("pinhole_au") or acq.get("pinhole_detector_um")):
        missing.append("pinhole_au")
    return missing


# ==============================================================================
# 2. THEORETICAL PSF
# ==============================================================================
def _debye(rho, z, wavelength, na, n, n_theta=160):
    """
    Scalar Debye (Born and Wolf) intensity PSF of an aplanatic objective, in the focus region:
        U(rho, z) = integral_0^alpha sqrt(cos t) J0(k rho sin t) exp(i k z cos t) sin t dt,   I = |U|^2
    with k = 2 pi n / wavelength and sin(alpha) = NA / n. rho and z in nm. Returns I[z, rho] (peak = 1).
    """
    from scipy.special import j0
    k = 2 * np.pi * n / wavelength
    alpha = np.arcsin(min(na / n, 0.999))
    theta = np.linspace(0, alpha, n_theta)
    weight = np.sqrt(np.cos(theta)) * np.sin(theta)
    dtheta = theta[1] - theta[0]
    U = np.zeros((len(z), len(rho)), dtype=complex)
    for t, w in zip(theta, weight):
        U += w * j0(k * rho * np.sin(t))[None, :] * np.exp(1j * k * z * np.cos(t))[:, None]
    I = np.abs(U * dtheta) ** 2
    return I / I.max()


def _fwhm(axis, profile):
    """Full width at half maximum of a profile peaking at 1 near axis = 0 (linear interpolation)."""
    half = 0.5 * profile.max()
    above = np.nonzero(profile >= half)[0]
    lo, hi = above[0], above[-1]
    def cross(i0, i1):
        x0, x1, y0, y1 = axis[i0], axis[i1], profile[i0], profile[i1]
        return x0 + (half - y0) * (x1 - x0) / (y1 - y0)
    left = axis[lo] if lo == 0 else cross(lo - 1, lo)
    right = axis[hi] if hi == len(axis) - 1 else cross(hi, hi + 1)
    return float(right - left)


def psf_widths(acq, confocal=True):
    """
    Widths of the PSF, in nm: {"sigma_xy_nm", "sigma_z_nm", "fwhm_xy_nm", "fwhm_z_nm", "pinhole_diameter_nm"...}.
    Confocal: PSF = excitation PSF x (detection PSF convolved with the pinhole projected in the sample).
    Not modelled: refractive index mismatch between the immersion and the mounting medium, aberrations.
    """
    na, n = float(acq["na"]), float(acq["refractive_index"])
    lam_ex, lam_em = float(acq["excitation_nm"]), float(acq["emission_nm"])
    step = 20.0                                   # nm, lateral grid
    n_grid = 256
    z = np.arange(-3000, 3001, 50.0)
    rho = np.arange(0, step * n_grid / 2 * 1.5, step / 2)
    h_em = _debye(rho, z, lam_em, na, n)
    out = {"model": "scalar Debye (Born and Wolf)", "na": na, "refractive_index": n,
           "excitation_nm": lam_ex, "emission_nm": lam_em}
    if not confocal:
        i0 = len(z) // 2
        fx = _fwhm(np.concatenate([-rho[::-1], rho]), np.concatenate([h_em[i0, ::-1], h_em[i0]]))
        fz = _fwhm(z, h_em[:, 0])
        out.update(fwhm_xy_nm=float(fx), fwhm_z_nm=float(fz), sigma_xy_nm=float(fx * FWHM_TO_SIGMA),
                   sigma_z_nm=float(fz * FWHM_TO_SIGMA))
        return out
    h_ex = _debye(rho, z, lam_ex, na, n)
    # pinhole projected in the sample (diameter, nm)
    if acq.get("pinhole_detector_um") and acq.get("magnification"):
        d_pin = acq["pinhole_detector_um"] * 1000.0 / acq["magnification"]
    elif acq.get("pinhole_au"):
        d_pin = acq["pinhole_au"] * 2.44 * lam_em / na          # 1 Airy unit = Airy disc diameter, in the sample
    else:
        d_pin = 2.44 * lam_em / na                              # 1 Airy unit by default
    out["pinhole_diameter_nm"] = float(d_pin)
    coords = (np.arange(n_grid) - n_grid // 2) * step
    X, Y = np.meshgrid(coords, coords)
    R = np.hypot(X, Y)
    disc = (R <= d_pin / 2).astype(float)
    disc /= disc.sum()
    disc_f = np.fft.rfft2(np.fft.ifftshift(disc))
    centre = n_grid // 2
    lateral = np.zeros((len(z), n_grid))
    axial = np.zeros(len(z))
    for iz in range(len(z)):
        det = np.interp(R, rho, h_em[iz])
        det = np.fft.irfft2(np.fft.rfft2(det) * disc_f, s=det.shape)
        exc = np.interp(R, rho, h_ex[iz])
        eff = exc * det
        lateral[iz] = eff[centre]
        axial[iz] = eff[centre, centre]
    peak = axial.max()
    i0 = int(np.argmax(axial))
    fx = _fwhm(coords, lateral[i0] / peak)
    fz = _fwhm(z, axial / peak)
    out.update(fwhm_xy_nm=float(fx), fwhm_z_nm=float(fz), sigma_xy_nm=float(fx * FWHM_TO_SIGMA),
               sigma_z_nm=float(fz * FWHM_TO_SIGMA))
    return out


def sigmas_in_voxels(widths, pixel_nm, step_nm):
    return float(widths["sigma_xy_nm"] / pixel_nm), float(widths["sigma_z_nm"] / step_nm)


# ==============================================================================
# 3. GAUSSIAN FIT OF ONE SPOT
# ==============================================================================
def _integrated_gauss(coord, centre, sigma):
    """Fraction of a unit Gaussian falling in each voxel (integrated over the voxel, width 1)."""
    from scipy.special import erf
    s = sigma * np.sqrt(2)
    return 0.5 * (erf((coord + 0.5 - centre) / s) - erf((coord - 0.5 - centre) / s))


def fit_spot(img, centre, background, sigma0, half_xy=None, half_z=3, fit_sigma_z=False):
    """
    Fits  I = background + N * gz(z) * gy(y) * gx(x)  (each factor: Gaussian integrated over the voxel) around
    `centre` = (z, y, x) in voxels. The background is given (not fitted). N is the integrated intensity of the
    spot above the background (counts x voxels, the sum of the whole Gaussian, tails included).
    Free parameters: z0, y0, x0, N, sigma_xy (sigma in voxels, bounded to 0.5-3 x the PSF value); sigma_z stays at
    the PSF value unless fit_sigma_z (it is hardly constrained with planes as thick as the PSF).
    sigma0 = (sigma_xy, sigma_z) of the PSF. Returns a dict (nan values if the fit fails); sigma_xy_se is the
    standard error of sigma_xy (large for dim spots: the size of a dim spot cannot be judged).
    """
    from scipy.optimize import least_squares
    fail = {"N": np.nan, "sigma_xy": np.nan, "sigma_xy_se": np.nan, "sigma_z": np.nan, "z": np.nan, "y": np.nan,
            "x": np.nan, "N_se": np.nan, "ok": False}
    if half_xy is None:
        half_xy = int(np.ceil(4 * sigma0[0])) + 1
    cz, cy, cx = (int(round(c)) for c in centre)
    z0, z1 = max(cz - half_z, 0), min(cz + half_z + 1, img.shape[0])
    y0, y1 = max(cy - half_xy, 0), min(cy + half_xy + 1, img.shape[1])
    x0, x1 = max(cx - half_xy, 0), min(cx + half_xy + 1, img.shape[2])
    win = img[z0:z1, y0:y1, x0:x1].astype(float)
    if win.size < 30:
        return fail
    zz = np.arange(z0, z1, dtype=float)
    yy = np.arange(y0, y1, dtype=float)
    xx = np.arange(x0, x1, dtype=float)
    excess = win - background
    n0 = max(float(excess.clip(0).sum()), 1.0)

    def model(p):
        gz = _integrated_gauss(zz, p[0], abs(p[5]) if fit_sigma_z else sigma0[1])
        gy = _integrated_gauss(yy, p[1], abs(p[4]))
        gx = _integrated_gauss(xx, p[2], abs(p[4]))
        return background + p[3] * gz[:, None, None] * gy[None, :, None] * gx[None, None, :]

    def resid(p):
        # Poisson maximum likelihood written as least squares: signed deviance residuals
        m = np.maximum(model(p), 1e-6)
        y = win
        with np.errstate(divide="ignore", invalid="ignore"):
            term = np.where(y > 0, y * np.log(y / m), 0.0)
        dev = 2 * (term - (y - m))
        return (np.sign(y - m) * np.sqrt(np.maximum(dev, 0.0))).ravel()

    p0 = np.array([centre[0], centre[1], centre[2], n0, sigma0[0], sigma0[1]], dtype=float)
    lower = [z0 - 1, y0 - 1, x0 - 1, 0.0, 0.5 * sigma0[0], 0.25 if fit_sigma_z else sigma0[1] * 0.999]
    upper = [z1, y1, x1, 20 * n0 + 100, 3.0 * sigma0[0], 6.0 * max(sigma0[1], 0.5) if fit_sigma_z else sigma0[1] * 1.001]
    try:
        res = least_squares(resid, p0, bounds=(lower, upper), method="trf", max_nfev=60)
    except Exception:
        return fail
    p = res.x
    se = se_sigma = np.nan
    try:
        jac = res.jac[:, :5]                    # sigma_z is not free in the default fit
        cov = np.linalg.inv(jac.T @ jac)
        se = float(np.sqrt(max(cov[3, 3], 0.0)))
        se_sigma = float(np.sqrt(max(cov[4, 4], 0.0)))
    except np.linalg.LinAlgError:
        pass
    return {"N": float(p[3]), "sigma_xy": float(abs(p[4])), "sigma_xy_se": se_sigma,
            "sigma_z": float(abs(p[5])) if fit_sigma_z else float(sigma0[1]), "z": float(p[0]),
            "y": float(p[1]), "x": float(p[2]), "N_se": se, "ok": bool(res.success)}
