# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2015, IBM
# Copyright 2015, Craig Tracey <craigtracey@gmail.com>
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import csv
import StringIO
import logging
import requests

from collections import OrderedDict
from giftwrap.builders.package_builder import PackageBuilder

BASE_PYPI_URL = 'http://pypi.python.org/pypi/%(package)s/%(version)s/json'
ordered_fieldnames = OrderedDict([
    ('project_name', None),
    ('package', None),
    ('version', None),
    ('homepage', None),
    ('license_info', None),
])

LOG = logging.getLogger(__name__)


class PackageMetaBuilder(PackageBuilder):

    def __init__(self, build_spec):
        super(PackageMetaBuilder, self).__init__(build_spec)
        self._project_dependencies = {}
        logging.getLogger("requests").setLevel(logging.WARNING)

    def _finalize_project_build(self, project):
        super(PackageMetaBuilder, self)._finalize_project_build(project)
        self._project_dependencies[project.name] = self._log_metadata(project)

    def _finalize_build(self):
        for project_name, deps_info in self._project_dependencies.iteritems():
            LOG.info("%s dependency metadata:\n%s", project_name,
                     deps_info.getvalue())

    def _log_metadata(self, project):
        dependencies = self._extract_dependencies(project)

        output = StringIO.StringIO()
        writer = csv.DictWriter(output, delimiter=',',
                                quoting=csv.QUOTE_MINIMAL,
                                fieldnames=ordered_fieldnames)

        for dep in dependencies:
            license, homepage = self._get_package_license_homepage(**dep)
            info = dep
            info['license_info'] = license
            info['homepage'] = homepage
            info['project_name'] = project.name
            writer.writerow(info)

        self._project_dependencies[project.name] = output

    def _get_package_license_homepage(self, package, version):
        url = BASE_PYPI_URL % locals()
        resp = requests.get(url)

        license = None
        homepage = None
        if resp.status_code == 200:
            data = resp.json()
            license = data['info'].get('license', None)
            homepage = data['info'].get('home_page', None)

        return license, homepage

    def _extract_dependencies(self, project):
        pip_path = self._get_venv_pip_path(project.install_path)
        cmd = "%s freeze" % pip_path
        freeze = self._execute(cmd)

        dependencies = []
        for dep in freeze.split('\n'):
            parts = dep.split('==')

            if len(parts) == 2:
                data = {'package': parts[0],
                        'version': parts[1]}
                dependencies.append(data)

        return dependencies
