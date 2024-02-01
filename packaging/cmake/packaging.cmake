set(CPACK_PACKAGE_VENDOR "University Library at The University of Illinois at Urbana Champaign: Preservation Services")
set(CPACK_WIX_UPGRADE_GUID C81EC876-C4BD-11E7-9268-005056C00008)
set(CPACK_WIX_PRODUCT_ICON "${PROJECT_SOURCE_DIR}/speedwagon/favicon.ico")
set(CPACK_PACKAGE_NAME Speedwagon)
set(CPACK_PACKAGE_INSTALL_DIRECTORY Speedwagon)
set(CPACK_WIX_PROGRAM_MENU_FOLDER Speedwagon)
set(CPACK_RESOURCE_FILE_LICENSE "${PROJECT_BINARY_DIR}/LICENSE.txt")

set(CPACK_WIX_EXTRA_SOURCES ${PROJECT_BINARY_DIR}/configs/install/wix_start_menu.wxs)

if(SPEEDWAGON_DOC_PDF)
    list(APPEND CPACK_WIX_EXTRA_SOURCES ${CMAKE_CURRENT_LIST_DIR}/docs.wxs)
    set(CPACK_WIX_PDF_COMPONENTREF "<ComponentRef Id=\"DocumentationShortcut\"/>")
 endif()

configure_file(${PROJECT_SOURCE_DIR}/packaging/cmake/templates/shortcuts.wxs.in configs/install/shortcuts.wxs @ONLY)
list(APPEND CPACK_WIX_EXTRA_SOURCES ${PROJECT_BINARY_DIR}/configs/install/shortcuts.wxs)

set(CPACK_WIX_PATCH_FILE ${PROJECT_SOURCE_DIR}/packaging/cmake/patch_wix.xml)

set(CPACK_NSIS_MENU_LINKS
    "http://www.library.illinois.edu/dccdocs/speedwagon;Documentation"
    )

set(CPACK_NSIS_CREATE_ICONS_EXTRA
    "CreateShortCut '$SMPROGRAMS\\\\Speedwagon\\\\Speedwagon.lnk' '$INSTDIR\\\\bin\\\\python.exe' '-m speedwagon' '$INSTDIR\\\\Lib\\\\site-packages\\\\Speedwagon\\\\favicon.ico'"
    )

set(CPACK_NSIS_DELETE_ICONS_EXTRA
    "Delete '$SMPROGRAMS\\\\Speedwagon\\\\Speedwagon.lnk'"
    )

set(CPACK_NSIS_EXTRA_INSTALL_COMMANDS "ExecWait '\\\"$INSTDIR\\\\bin\\\\python.exe\\\" -m compileall -f $INSTDIR\\\\Lib'")
set(CPACK_NSIS_HELP_LINK "http://www.library.illinois.edu/dccdocs/speedwagon")
set(CPACK_NSIS_EXECUTABLES_DIRECTORY bin)

if(DEFINED ENV{build_number})
    string(TOLOWER ${CMAKE_SYSTEM_PROCESSOR} PROCESSOR_TYPE)
    if(NOT DEFINED CPACK_PACKAGE_VERSION_MAJOR)
        if(DEFINED SPEEDWAGON_VERSION_MAJOR)
            message(STATUS "setting CPACK_PACKAGE_VERSION_MAJOR to ${SPEEDWAGON_VERSION_MAJOR}")
            set(CPACK_PACKAGE_VERSION_MAJOR "${SPEEDWAGON_VERSION_MAJOR}")
        endif()
    endif()
    if(NOT DEFINED CPACK_PACKAGE_VERSION_MINOR)
        if(DEFINED SPEEDWAGON_VERSION_MINOR)
            message(STATUS "setting CPACK_PACKAGE_VERSION_MINOR to ${SPEEDWAGON_VERSION_MINOR}")
            set(CPACK_PACKAGE_VERSION_MINOR "${SPEEDWAGON_VERSION_MINOR}")
        endif()
    endif()
    if(NOT DEFINED CPACK_PACKAGE_VERSION_PATCH)
        if(DEFINED SPEEDWAGON_VERSION_PATCH)
            message(STATUS "setting CPACK_PACKAGE_VERSION_PATCH to ${SPEEDWAGON_VERSION_PATCH}")
            set(CPACK_PACKAGE_VERSION_PATCH "${SPEEDWAGON_VERSION_PATCH}")
        endif()
    endif()

    set(CPACK_PACKAGE_FILE_NAME ${CPACK_PACKAGE_NAME}-${CPACK_PACKAGE_VERSION_MAJOR}.${CPACK_PACKAGE_VERSION_MINOR}.${CPACK_PACKAGE_VERSION_PATCH}-$ENV{build_number}-${PROCESSOR_TYPE})
endif()

configure_file(${PROJECT_SOURCE_DIR}/packaging/cmake/templates/wix_start_menu.wvs.in configs/install/wix_start_menu.wxs @ONLY)

