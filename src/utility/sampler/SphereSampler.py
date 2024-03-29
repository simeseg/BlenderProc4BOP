import numpy as np
import mathutils


class SphereSampler:
    """ Samples a point from the surface or from the interior of solid sphere

    Gaussian is spherically symmetric. Sample from three independent Gaussian distributions
    the direction of the vector inside the sphere. Then scalculate magnitude based on the operation mode.

    **Configuration**:

    .. csv-table::
       :header: "Parameter", "Description"

       "center", "A list of three values, describing the x, y and z coordinate of the center of the sphere."
       "radius", "The radius of the sphere."
       "mode", "Mode of sampling. SURFACE - sampling from the surface of the sphere, INTERIOR = sampling from the interior of the sphere."

    """

    # https://math.stackexchange.com/a/87238
    # https://math.stackexchange.com/a/1585996
    @staticmethod
    def sample(config):
        """
        :param config: A configuration object containing the parameters necessary to sample.
        :return: A random point lying inside or on the surface of a solid sphere. Type: Mathutils vector
        """
        # Center of the sphere.
        center = np.array(config.get_list("center"))
        # Radius of the sphere.
        radius = config.get_float("radius")
        # Mode of operation.
        mode = config.get_string("mode")
        
        # Sample
        direction = np.random.normal(size=3)
        
        if np.count_nonzero(direction) == 0:  # Check no division by zero
            direction[0] = 1e-5

        # For normalization
        norm = direction.dot(direction)**(0.5)

        # If sampling from the surface set magnitude to radius of the sphere
        if mode == "SURFACE":
            magnitude = radius
        # If sampling from the interior set it to uniformly sampled value
        elif mode == "INTERIOR":
            magnitude = radius * np.random.unform()**(1./3)
        else:
            raise Exception("Unknows sampling mode: " + mode)
        
        # Normalize
        sampled_point = list(map(lambda x: magnitude*x/norm, direction))
        
        # Add center
        location = mathutils.Vector(np.array(sampled_point) + center)

        return location
