################################################################################
#
# iree-runtime
#
################################################################################

IREE_RUNTIME_VERSION = b46def4476d709db249406e0ca3b9a59a16a5196
IREE_RUNTIME_SITE = $(realpath $(BR2_EXTERNAL_APOLLO_QBOX_PATH)/../../../../sources/iree)
IREE_RUNTIME_SITE_METHOD = local
IREE_RUNTIME_LICENSE = Apache-2.0 WITH LLVM-exception
IREE_RUNTIME_LICENSE_FILES = LICENSE
IREE_RUNTIME_SUPPORTS_IN_SOURCE_BUILD = NO
IREE_RUNTIME_CMAKE_BACKEND = ninja
IREE_RUNTIME_DEPENDENCIES = host-iree-runtime host-python3
IREE_RUNTIME_APOLLO_GUEST_TOOLS = $(BR2_EXTERNAL_APOLLO_QBOX_PATH)/board/apollo/apollo-qbox/guest-tools
IREE_RUNTIME_APOLLO_GUEST_TOOLS_BUILD = $(@D)/apollo-qbox-guest-tools

IREE_RUNTIME_CONF_OPTS = \
	-DBUILD_SHARED_LIBS=OFF \
	-DIREE_BUILD_COMPILER=OFF \
	-DIREE_BUILD_TESTS=OFF \
	-DIREE_BUILD_SAMPLES=OFF \
	-DIREE_BUILD_BENCHMARKS=OFF \
	-DIREE_BUILD_PYTHON_BINDINGS=OFF \
	-DIREE_BUILD_ALL_CHECK_TEST_MODULES=OFF \
	-DIREE_ERROR_ON_MISSING_SUBMODULES=OFF \
	-DIREE_HOST_BIN_DIR=$(HOST_DIR)/bin \
	-DPython3_EXECUTABLE=$(HOST_DIR)/bin/python3 \
	-DIREE_HAL_DRIVER_DEFAULTS=OFF \
	-DIREE_HAL_DRIVER_LOCAL_SYNC=ON \
	-DIREE_HAL_DRIVER_LOCAL_TASK=ON \
	-DIREE_HAL_EXECUTABLE_LOADER_DEFAULTS=OFF \
	-DIREE_HAL_EXECUTABLE_LOADER_EMBEDDED_ELF=ON \
	-DIREE_HAL_EXECUTABLE_PLUGIN_DEFAULTS=ON

IREE_RUNTIME_BUILD_OPTS = --target iree-run-module

define IREE_RUNTIME_BUILD_APOLLO_FRONTEND
	mkdir -p $(IREE_RUNTIME_APOLLO_GUEST_TOOLS_BUILD)/bin \
		$(IREE_RUNTIME_APOLLO_GUEST_TOOLS_BUILD)/lib
	$(TARGET_CC) $(TARGET_CFLAGS) -Os -Wall -Wextra -Werror \
		-I$(IREE_RUNTIME_APOLLO_GUEST_TOOLS) \
		$(IREE_RUNTIME_APOLLO_GUEST_TOOLS)/apollo_iree_run_module.c \
		$(IREE_RUNTIME_APOLLO_GUEST_TOOLS)/apollo_iree_hal_registry.c \
		$(IREE_RUNTIME_APOLLO_GUEST_TOOLS)/apollo_iree_hexagon_hal.c \
		$(TARGET_LDFLAGS) -ldl \
		-o $(IREE_RUNTIME_APOLLO_GUEST_TOOLS_BUILD)/bin/apollo-iree-run-module
	$(TARGET_CC) $(TARGET_CFLAGS) -Os -Wall -Wextra -Werror \
		-I$(IREE_RUNTIME_APOLLO_GUEST_TOOLS) \
		$(IREE_RUNTIME_APOLLO_GUEST_TOOLS)/apollo_iree_hexagon_runner.c \
		$(IREE_RUNTIME_APOLLO_GUEST_TOOLS)/apollo_iree_hexagon_hal.c \
		$(TARGET_LDFLAGS) -ldl \
		-o $(IREE_RUNTIME_APOLLO_GUEST_TOOLS_BUILD)/bin/apollo-iree-hexagon-runner
	$(TARGET_CC) $(TARGET_CFLAGS) -Os -Wall -Wextra -Werror \
		-I$(IREE_RUNTIME_APOLLO_GUEST_TOOLS) \
		$(IREE_RUNTIME_APOLLO_GUEST_TOOLS)/apollo_hexagon_apko_negative.c \
		$(TARGET_LDFLAGS) \
		-o $(IREE_RUNTIME_APOLLO_GUEST_TOOLS_BUILD)/bin/apollo-hexagon-apko-negative
	$(TARGET_CC) $(TARGET_CFLAGS) -Os -Wall -Wextra -Werror \
		-fPIC -shared \
		-I$(IREE_RUNTIME_APOLLO_GUEST_TOOLS) \
		$(IREE_RUNTIME_APOLLO_GUEST_TOOLS)/apollo_iree_hexagon_plugin.c \
		$(IREE_RUNTIME_APOLLO_GUEST_TOOLS)/apollo_iree_hexagon_hal.c \
		$(TARGET_LDFLAGS) \
		-o $(IREE_RUNTIME_APOLLO_GUEST_TOOLS_BUILD)/lib/libapollo_iree_hexagon_hal_plugin.so
endef

IREE_RUNTIME_POST_BUILD_HOOKS += IREE_RUNTIME_BUILD_APOLLO_FRONTEND

define IREE_RUNTIME_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 $(@D)/buildroot-build/tools/iree-run-module \
		$(TARGET_DIR)/usr/libexec/qbox/iree-run-module.real
	$(INSTALL) -D -m 0755 $(IREE_RUNTIME_APOLLO_GUEST_TOOLS)/iree-run-module-wrapper.sh \
		$(TARGET_DIR)/usr/bin/iree-run-module
	$(INSTALL) -D -m 0755 $(IREE_RUNTIME_APOLLO_GUEST_TOOLS_BUILD)/bin/apollo-iree-run-module \
		$(TARGET_DIR)/usr/bin/apollo-iree-run-module
	$(INSTALL) -D -m 0755 $(IREE_RUNTIME_APOLLO_GUEST_TOOLS_BUILD)/bin/apollo-iree-hexagon-runner \
		$(TARGET_DIR)/usr/bin/apollo-iree-hexagon-runner
	$(INSTALL) -D -m 0755 $(IREE_RUNTIME_APOLLO_GUEST_TOOLS_BUILD)/bin/apollo-hexagon-apko-negative \
		$(TARGET_DIR)/usr/bin/apollo-hexagon-apko-negative
	$(INSTALL) -D -m 0755 $(IREE_RUNTIME_APOLLO_GUEST_TOOLS_BUILD)/lib/libapollo_iree_hexagon_hal_plugin.so \
		$(TARGET_DIR)/usr/lib/qbox/libapollo_iree_hexagon_hal_plugin.so
endef

HOST_IREE_RUNTIME_SITE = $(IREE_RUNTIME_SITE)
HOST_IREE_RUNTIME_SITE_METHOD = local
HOST_IREE_RUNTIME_LICENSE = $(IREE_RUNTIME_LICENSE)
HOST_IREE_RUNTIME_LICENSE_FILES = $(IREE_RUNTIME_LICENSE_FILES)
HOST_IREE_RUNTIME_SUPPORTS_IN_SOURCE_BUILD = NO
HOST_IREE_RUNTIME_CMAKE_BACKEND = ninja
HOST_IREE_RUNTIME_DEPENDENCIES = host-python3

HOST_IREE_RUNTIME_CONF_OPTS = \
	-DBUILD_SHARED_LIBS=OFF \
	-DIREE_BUILD_COMPILER=OFF \
	-DIREE_BUILD_TESTS=OFF \
	-DIREE_BUILD_SAMPLES=OFF \
	-DIREE_BUILD_BENCHMARKS=OFF \
	-DIREE_BUILD_PYTHON_BINDINGS=OFF \
	-DIREE_BUILD_ALL_CHECK_TEST_MODULES=OFF \
	-DIREE_ERROR_ON_MISSING_SUBMODULES=OFF \
	-DPython3_EXECUTABLE=$(HOST_DIR)/bin/python3 \
	-DIREE_HAL_DRIVER_DEFAULTS=OFF \
	-DIREE_HAL_DRIVER_LOCAL_SYNC=ON \
	-DIREE_HAL_DRIVER_LOCAL_TASK=ON \
	-DIREE_HAL_EXECUTABLE_LOADER_DEFAULTS=OFF \
	-DIREE_HAL_EXECUTABLE_LOADER_EMBEDDED_ELF=ON \
	-DIREE_HAL_EXECUTABLE_PLUGIN_DEFAULTS=ON

HOST_IREE_RUNTIME_BUILD_OPTS = \
	--target iree-flatcc-cli \
	--target iree-c-embed-data

define HOST_IREE_RUNTIME_INSTALL_CMDS
	$(INSTALL) -D -m 0755 $(@D)/buildroot-build/tools/iree-flatcc-cli \
		$(HOST_DIR)/bin/iree-flatcc-cli
	$(INSTALL) -D -m 0755 $(@D)/buildroot-build/tools/iree-c-embed-data \
		$(HOST_DIR)/bin/iree-c-embed-data
endef

$(eval $(cmake-package))
$(eval $(host-cmake-package))
