import os
import bpy
import time
import inspect
import importlib
from src.utility.Config import Config
from mathutils import Vector
from copy import deepcopy

class Utility:
    working_dir = ""

    @staticmethod
    def initialize_modules(module_configs, global_config):
        """ Initializes the modules described in the given configuration.

        Example for module_configs:
        [{
          "name": "base.ModuleA",
          "config": {...}
        }, ...]

        Here the name contains the path to the module class, starting from inside the src directory.

        Example for global_config:
        {"base": {
            param: 42
        }}

        In this way all modules with prefix "base" will inherit "param" into their configuration.
        Local config always overwrites global.
        Parameters specified under "all" in the global config are inherited by all modules.

        :param module_configs: A list of dicts, each one describing one module.
        :param global_config: A dict containing the global configuration.
        :return:
        """
        modules = []
        all_base_config = global_config["all"] if "all" in global_config else {}

        for module_config in module_configs:
            # If only the module name is given (short notation)
            if isinstance(module_config, str):
                module_config = {"name": module_config}

            # Merge global and local config (local overwrites global)
            model_type = module_config["name"].split(".")[0]
            base_config = global_config[model_type] if model_type in global_config else {}

            # Initialize config with all_base_config
            config = deepcopy(all_base_config)
            # Overwrite with module type base config
            Utility.merge_dicts(base_config, config)
            # Check if there is a module specific config
            if "config" in module_config:
                # Overwrite with module specific config
                Utility.merge_dicts(module_config["config"], config)

            with Utility.BlockStopWatch("Initializing module " + module_config["name"]):
                # Import file and extract class
                module_class = getattr(importlib.import_module("src." + module_config["name"]), module_config["name"].split(".")[-1])
                # Create module
                modules.append(module_class(Config(config)))

        return modules

    @staticmethod
    def transform_point_to_blender_coord_frame(point, frame_of_point):
        """ Transforms the given point into the blender coordinate frame.

        Example: [1, 2, 3] and ["X", "-Z", "Y"] => [1, -3, 2]

        :param point: The point to convert in form of a list or mathutils.Vector.
        :param frame_of_point: An array containing three elements, describing the axes of the coordinate frame the point is in. (Allowed values: "X", "Y", "Z", "-X", "-Y", "-Z")
        :return: The converted point also in form of a list or mathutils.Vector.
        """
        assert(len(frame_of_point) == 3, "The specified coordinate frame has more or less than tree axes: " + str(frame_of_point))

        output = []
        for i, axis in enumerate(frame_of_point):
            axis = axis.upper()

            if axis.endswith("X"):
                output.append(point[0])
            elif axis.endswith("Y"):
                output.append(point[1])
            elif axis.endswith("Z"):
                output.append(point[2])
            else:
                raise Exception("Invalid axis: " + axis)

            if axis.startswith("-"):
                output[-1] *= -1

        # Depending on the given type, return a vector or a list
        if isinstance(point, Vector):
            return Vector(output)
        else:
            return output

    @staticmethod
    def resolve_path(path):
        """ Returns an absolute path. If given path is relative, current working directory is put in front.

        :param path: The path to resolve.
        :return: The absolute path.
        """
        path = path.strip()

        if path.startswith("/"):
            return path
        else:
            return os.path.join(os.path.dirname(Utility.working_dir), path)

    @staticmethod
    def merge_dicts(source, destination):
        """ Recursively copies all key value pairs from src to dest (Overwrites existing)

        :param source: The source dict.
        :param destination: The destination dict
        :return: The modified destination dict.
        """
        for key, value in source.items():
            if isinstance(value, dict):
                # get node or create one
                node = destination.setdefault(key, {})
                Utility.merge_dicts(value, node)
            else:
                destination[key] = value

        return destination

    @staticmethod
    def hex_to_rgba(hex):
        """ Converts the given hex string to rgba color values.

        :param hex: The hex string, describing rgb.
        :return: The rgba color, in form of a list. Values between 0 and 1.
        """
        return [x / 255 for x in bytes.fromhex(hex[-6:])] + [1.0]

    @staticmethod
    def rgb_to_hex(rgb):
        """ Converts the given rgb to hex values.

        :param rgb: tuple of three with rgb integers.
        :return: Hex string.
        """
        return '#%02x%02x%02x' % tuple(rgb)

    @staticmethod
    def get_idx(array,item):
        """
        Returns index of an element if it exists in the list
        :param array: a list with values for which == operator works.
        :param item: item to find the index of
        :return: index of item, -1 otherwise
        """
        try:
            return array.index(item)
        except ValueError:
            return -1

    @staticmethod
    def insert_node_instead_existing_link(links, source_socket, new_node_dest_socket, new_node_src_socket, dest_socket):
        """ Replaces the node between source_socket and dest_socket with a new node.

        Before: source_socket -> dest_socket
        After: source_socket -> new_node_dest_socket
               new_node_src_socket -> dest_socket

        :param links: The collection of all links.
        :param source_socket: The source socket.
        :param new_node_dest_socket: The new destination for the link starting from source_socket.
        :param new_node_src_socket: The new source for the link towards dest_socket.
        :param dest_socket: The destination socket
        """
        for l in links:
            if l.from_socket == source_socket or l.to_socket == dest_socket:
                links.remove(l)

        links.new(source_socket, new_node_dest_socket)
        links.new(new_node_src_socket, dest_socket)

    class BlockStopWatch:
        """ Calls a print statement to mark the start and end of this block and also measures execution time.

        Usage: with BlockStopWatch('text'):
        """
        def __init__(self, block_name):
            self.block_name = block_name

        def __enter__(self):
            print("#### Start - " + self.block_name + " ####")
            self.start = time.time()

        def __exit__(self, type, value, traceback):
            print("#### Finished - " + self.block_name + " (took " + ("%.3f" % (time.time() - self.start)) + " seconds) ####")

    class UndoAfterExecution:
        """ Reverts all changes done to the blender project inside this block.

        Usage: with UndoAfterExecution():
        """
        def __init__(self, check_point_name=None):
            if check_point_name is None:
                check_point_name = inspect.stack()[1].filename + " - " + inspect.stack()[1].function
            self.check_point_name = check_point_name

        def __enter__(self):
            bpy.ops.ed.undo_push(message="before " + self.check_point_name)

        def __exit__(self, type, value, traceback):
            bpy.ops.ed.undo_push(message="after " + self.check_point_name)
            # The current state points to "after", now by calling undo we go back to "before"
            bpy.ops.ed.undo()

    @staticmethod
    def sample(name, parameters):
        """ A general sample function.

        It first builds the required sampler and then calls its sample function.

        :param name: The name of the sampler class.
        :param parameters: A dict containing the parameters that should be used to sample.
        :return: The sampled value.
        """
        # Import class from src.utility
        module_class = getattr(importlib.import_module("src.utility.sampler." + name), name.split(".")[-1])
        # Build configuration
        config = Config(parameters)
        # Call sample method
        return module_class.sample(config)

    @staticmethod
    def sample_based_on_config(config):
        """ A general sample function using the sampler and sample parameters described in the given config.

        The given config should follow the following scheme:

        {
          "name": "<name of sampler class>"
          "parameters": {
            <sampler parameters>
          }
        }

        :param config: A Configuration object or a dict containing the configuration data.
        :return: The sampled value.
        """
        if isinstance(config, dict):
            config = Config(config)

        return Utility.sample(config.get_string("name"), config.get_raw_dict("parameters"))
