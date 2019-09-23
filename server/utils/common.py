# -*- coding:utf-8 -*-

import os
import yaml

class Common(object):
    def __init__(self, logger):
        self._logger = logger

    def output(self, msg, level=None, color=None, light=False):
        """Generate output to CLI and log file
        """
        self._logger.write(msg, level=level, color=color, light=light)

    def _storeYAML(self, yaml_file, data):
        """Store data in YAML file
        """
        with open(yaml_file, 'wt') as raw:
            raw.write(yaml.dump(data, default_flow_style=False, indent=4))

        return True

    def _parseYAML(self, yaml_file):
        """Parse YAML file and return object generated
        """
        with open(yaml_file, 'rt') as stream:
            cfg = yaml.load(stream.read())
        
        return cfg

    def _mkdir_p(self, path):
        self.output('Create {d} directory...'.format(d=path), level="DEBUG")
        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == os.errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise exc

        return True