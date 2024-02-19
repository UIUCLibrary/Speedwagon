from unittest.mock import Mock, MagicMock

from speedwagon.frontend import interaction


# class TestAbstractPackageBrowser:
#     def test_get_packages(self, monkeypatch):
#         package_factory = Mock(spec=interaction.PackageFactory)
#         package_factory.locate_packages = Mock(return_value=[])
#         with monkeypatch.context() as context:
#             context.setattr(
#                 interaction,
#                 "PackageFactory",
#                 Mock(return_value=package_factory)
#             )
#             interaction.AbstractPackageBrowser.get_packages(
#                 root_dir="somepath",
#                 image_type=interaction.SupportedImagePackageFormats.JP2
#             )
#         assert package_factory.locate_packages.called is True
