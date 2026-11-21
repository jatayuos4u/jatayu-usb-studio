cmake_minimum_required(VERSION 3.20)
project(jatayu-usb-studio VERSION 1.1.0 LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
find_package(Qt6 REQUIRED COMPONENTS Widgets)
add_executable(jatayu-usb-studio src/main.cpp assets.qrc)
target_link_libraries(jatayu-usb-studio PRIVATE Qt6::Widgets)
set(studio_backend
    studio_operations.py
    windows_installer.py
    windows_udf.py
    studio_device_safety.py
    privileged_writer_contract.py
    verified_write_transaction.py
    udisks2_backend.py
    safety_backend.py
    simulation_backend.py
    writer_guard.py
    iso_write_preflight.py
    file_backed_writer.py
    file_copy_demo_cli.py
)
file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/backend")
foreach(module IN LISTS studio_backend)
    configure_file("${module}" "backend/${module}" COPYONLY)
endforeach()
install(TARGETS jatayu-usb-studio RUNTIME DESTINATION bin)
install(FILES jatayu-usb-studio.desktop DESTINATION share/applications)
install(FILES assets/icon.png DESTINATION share/icons/hicolor/512x512/apps RENAME jatayu-usb-studio.png)
install(FILES ${studio_backend} DESTINATION lib/jatayu-usb-studio)
install(FILES README.md LICENSE CREDITS.md THIRD_PARTY_NOTICES.md DESTINATION share/doc/jatayu-usb-studio)

set(CPACK_PACKAGE_NAME jatayu-usb-studio)
set(CPACK_PACKAGE_VERSION "1.1.0-1")
set(CPACK_DEBIAN_FILE_NAME DEB-DEFAULT)
set(CPACK_DEBIAN_PACKAGE_MAINTAINER "JatayuOS")
set(CPACK_DEBIAN_PACKAGE_SECTION utils)
set(CPACK_DEBIAN_PACKAGE_HOMEPAGE "https://jatayuos.in")
set(CPACK_DEBIAN_PACKAGE_DESCRIPTION "USB imaging and filesystem utility for JatayuOS")
set(CPACK_DEBIAN_PACKAGE_DEPENDS "libc6, libblkid1, libgcc-s1, libstdc++6, libqt6core6t64, libqt6gui6, libqt6widgets6, qt6-qpa-plugins, python3, python3-gi, gir1.2-glib-2.0, udisks2, dbus, polkitd, util-linux, coreutils, systemd, dosfstools, exfatprogs, ntfs-3g, e2fsprogs, ca-certificates, python3-pycdlib, libudfread0, mtools, wimtools")
set(CPACK_DEBIAN_PACKAGE_RECOMMENDS "polkit-kde-agent-1, qt6-wayland")
set(CPACK_GENERATOR DEB)
include(CPack)

include(CTest)
if(BUILD_TESTING)
    add_executable(studio-ui-test src/main.cpp assets.qrc)
    target_compile_definitions(studio-ui-test PRIVATE JATAYU_UI_TEST)
    target_link_libraries(studio-ui-test PRIVATE Qt6::Widgets)
    add_test(NAME StudioNavigation COMMAND studio-ui-test)
    set_tests_properties(StudioNavigation PROPERTIES ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
endif()
