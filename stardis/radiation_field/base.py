import numpy as np
import logging
from stardis.radiation_field.opacities import Opacities
from stardis.radiation_field.opacities.opacities_solvers import calc_alphas
from stardis.radiation_field.radiation_field_solvers import raytrace
from stardis.radiation_field.source_functions.blackbody import blackbody_flux_at_nu
from tardis.io.util import HDFWriterMixin

logger = logging.getLogger(__name__)


class RadiationField(HDFWriterMixin):
    """
    Class containing information about the radiation field.
    ###TODO Radiation field temperature should be a separate attribute, for the case of differing gas and radiation.

    Parameters
    ----------
    frequencies : astronopy.units.Quantity
    source_function : stardis.radiation_field.source_function
    stellar_model : stardis.stellar_model.StellarModel
    num_of_thetas : int

    Attributes
    ----------
    frequencies : astropy.units.Quantity
        Frequencies of the radiation field.
    source_function : stardis.radiation_field.source_function
        Source function of the radiation field.
    opacities : stardis.radiation_field.opacities
        Opacities object. Contains a dictionary of opacities contributed from different sources and the calc_total_alphas() method to
        calculate the total opacity at each frequency at each depth point.
    F_nu : numpy.ndarray
        Radiation field fluxes at each frequency at each depth point. Initialized as zeros and calculated by a solver.
    thetas : numpy.ndarray
        Theta angles for raytracing.
    I_nus_weights : numpy.ndarray
        Weights for the theta angles.
    I_nus : numpy.ndarray
        Radiation field intensity at each frequency at each depth point at each theta angle. Initialized as zeros and calculated by a solver.
    """

    hdf_properties = ["frequencies", "opacities", "F_nu"]

    def __init__(self, frequencies, source_function, stellar_model, num_of_thetas):
        self.frequencies = frequencies
        self.source_function = source_function
        self.opacities = Opacities(frequencies, stellar_model)
        self.F_nu = np.zeros((stellar_model.no_of_depth_points, len(frequencies)))

        # This uses gauss-legendre quadrature to sample thetas
        thetas, weights = np.polynomial.legendre.leggauss(num_of_thetas)
        self.thetas = (thetas / 2) + 0.5 * np.pi / 2
        self.I_nus_weights = weights * np.pi / 2

        # This was our original theta sampling method
        # dtheta = (np.pi / 2) / num_of_thetas  # Korg uses Gauss-Legendre quadrature here
        # start_theta = dtheta / 2
        # end_theta = (np.pi / 2) - (dtheta / 2)
        # self.thetas = np.linspace(start_theta, end_theta, num_of_thetas)
        # self.I_nus_weights = (
        #     2 * np.pi * dtheta * np.sin(self.thetas) * np.cos(self.thetas)
        # )

        self.I_nus = np.zeros(
            (stellar_model.no_of_depth_points, len(frequencies), len(self.thetas))
        )


def create_stellar_radiation_field(tracing_nus, stellar_model, stellar_plasma, config):
    """
    Create a stellar radiation field.

    This function creates a stellar radiation field by initializing a `RadiationField`
    object and calculating the alpha values for the stellar plasma. It then performs
    raytracing on the stellar model.

    Parameters
    ----------
    tracing_nus : array
        The frequencies at which to trace the radiation field.
    stellar_model : StellarModel
        The stellar model to use for the radiation field.
    stellar_plasma : StellarPlasma
        The stellar plasma to use for the radiation field.
    config : Config
        The configuration object containing the opacity and threading settings.

    Returns
    -------
    stellar_radiation_field : RadiationField
        The created stellar radiation field.

    """

    stellar_radiation_field = RadiationField(
        tracing_nus, blackbody_flux_at_nu, stellar_model, config.no_of_thetas
    )
    logger.info("Calculating alphas")
    calc_alphas(
        stellar_plasma=stellar_plasma,
        stellar_model=stellar_model,
        stellar_radiation_field=stellar_radiation_field,
        opacity_config=config.opacity,
        n_threads=config.n_threads,
    )
    logger.info("Raytracing")
    raytrace(
        stellar_model,
        stellar_radiation_field,
        n_threads=config.n_threads,
    )

    return stellar_radiation_field
