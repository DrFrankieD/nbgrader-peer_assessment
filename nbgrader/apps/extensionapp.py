import io
import os.path
import json
import sys
import six

from jupyter_core.paths import jupyter_config_dir
from notebook.nbextensions import InstallNBExtensionApp, EnableNBExtensionApp, DisableNBExtensionApp, flags, aliases
from traitlets import Unicode
from traitlets.config import Config
from traitlets.config.application import catch_config_error
from traitlets.config.application import Application
from traitlets.config.loader import JSONFileConfigLoader, ConfigFileNotFound

from .baseapp import NbGrader, format_excepthook

install_flags = {}
install_flags.update(flags)
install_aliases = {}
install_aliases.update(aliases)
del install_aliases['destination']
class ExtensionInstallApp(InstallNBExtensionApp, NbGrader):

    name = u'nbgrader-extension-install'
    description = u'Install the nbgrader extension'

    flags = install_flags
    aliases = install_aliases

    examples = """
        nbgrader extension install
        nbgrader extension install --user
        nbgrader extension install --prefix=/path/to/prefix
        nbgrader extension install --nbextensions=/path/to/nbextensions
    """

    destination = Unicode('')

    def _classes_default(self):
        return [ExtensionInstallApp, InstallNBExtensionApp]

    def excepthook(self, etype, evalue, tb):
        format_excepthook(etype, evalue, tb)

    def start(self):
        nbextensions_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'nbextensions'))
        extra_args = self.extra_args[:]

        # install the create_assignment extension
        if len(extra_args) == 0 or "create_assignment" in extra_args:
            self.log.info("Installing create_assignment extension")
            self.extra_args = [os.path.join(nbextensions_dir, 'create_assignment')]
            self.destination = 'create_assignment'
            self.install_extensions()

        # install the assignment_list extension
        if sys.platform != 'win32' and (len(extra_args) == 0 or "assignment_list" in extra_args):
            self.log.info("Installing assignment_list extension")
            self.extra_args = [os.path.join(nbextensions_dir, 'assignment_list', 'static')]
            self.destination = 'assignment_list'
            self.install_extensions()


class ExtensionActivateApp(EnableNBExtensionApp, NbGrader):

    name = u'nbgrader-extension-activate'
    description = u'Activate the nbgrader extension'

    flags = {}
    aliases = {}

    examples = """
        nbgrader extension activate
    """

    def _classes_default(self):
        return [ExtensionActivateApp, EnableNBExtensionApp]

    def enable_server_extension(self, extension):
        loader = JSONFileConfigLoader('jupyter_notebook_config.json', jupyter_config_dir())
        try:
            config = loader.load_config()
        except ConfigFileNotFound:
            config = Config()

        if 'server_extensions' not in config.NotebookApp:
            config.NotebookApp.server_extensions = []
        if extension not in config.NotebookApp.server_extensions:
            config.NotebookApp.server_extensions.append(extension)

        # save the updated config
        with io.open(os.path.join(jupyter_config_dir(), 'jupyter_notebook_config.json'), 'w+') as f:
            f.write(six.u(json.dumps(config, indent=2)))

    def start(self):
        if len(self.extra_args) == 0 or "create_assignment" in self.extra_args:
            self.log.info("Activating create_assignment nbextension")
            self.section = "notebook"
            self.enable_nbextension("create_assignment/main")

        if sys.platform != 'win32' and (len(self.extra_args) == 0 or "assignment_list" in self.extra_args):
            self.log.info("Activating assignment_list server extension")
            self.enable_server_extension('nbgrader.nbextensions.assignment_list')

            self.log.info("Activating assignment_list nbextension")
            self.section = "tree"
            self.enable_nbextension("assignment_list/main")

        self.log.info("Done. You may need to restart the Jupyter notebook server for changes to take effect.")


class ExtensionDeactivateApp(DisableNBExtensionApp, NbGrader):

    name = u'nbgrader-extension-deactivate'
    description = u'Deactivate the nbgrader extension'

    flags = {}
    aliases = {}

    examples = """
        nbgrader extension deactivate
    """

    def _classes_default(self):
        return [ExtensionDeactivateApp, DisableNBExtensionApp]

    def _recursive_get(self, obj, key_list):
        if obj is None or len(key_list) == 0:
            return obj
        return self._recursive_get(obj.get(key_list[0], None), key_list[1:])

    def disable_server_extension(self, extension):
        loader = JSONFileConfigLoader('jupyter_notebook_config.json', jupyter_config_dir())
        try:
            config = loader.load_config()
        except ConfigFileNotFound:
            config = Config()

        if 'server_extensions' not in config.NotebookApp:
            return
        if extension not in config.NotebookApp.server_extensions:
            return

        config.NotebookApp.server_extensions.remove(extension)

        # save the updated config
        with io.open(os.path.join(jupyter_config_dir(), 'jupyter_notebook_config.json'), 'w+') as f:
            f.write(six.u(json.dumps(config, indent=2)))

    def start(self):
        if len(self.extra_args) == 0 or "create_assignment" in self.extra_args:
            self.log.info("Deactivating create_assignment nbextension")
            self.section = "notebook"
            self.disable_nbextension("create_assignment/main")

        if sys.platform != 'win32' and (len(self.extra_args) == 0 or "assignment_list" in self.extra_args):
            self.log.info("Deactivating assignment_list server extension")
            self.disable_server_extension('nbgrader.nbextensions.assignment_list')

            self.log.info("Deactivating assignment_list nbextension")
            self.section = "tree"
            self.disable_nbextension("assignment_list/main")

        self.log.info("Done. You may need to restart the Jupyter notebook server for changes to take effect.")


class ExtensionApp(NbGrader):

    name = u'nbgrader extension'
    description = u'Utilities for managing the nbgrader extension'
    examples = ""

    subcommands = dict(
        install=(
            ExtensionInstallApp,
            "Install the extension."
        ),
        activate=(
            ExtensionActivateApp,
            "Activate the extension."
        ),
        deactivate=(
            ExtensionDeactivateApp,
            "Deactivate the extension."
        )
    )

    def _classes_default(self):
        classes = super(ExtensionApp, self)._classes_default()

        # include all the apps that have configurable options
        for appname, (app, help) in self.subcommands.items():
            if len(app.class_traits(config=True)) > 0:
                classes.append(app)

        return classes

    @catch_config_error
    def initialize(self, argv=None):
        super(ExtensionApp, self).initialize(argv)

    def start(self):
        # check: is there a subapp given?
        if self.subapp is None:
            self.print_help()
            sys.exit(1)

        # This starts subapps
        super(ExtensionApp, self).start()
