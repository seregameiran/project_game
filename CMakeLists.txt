cmake_minimum_required(VERSION 3.10)
project(SFML_Project)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(SFML 2.6 COMPONENTS graphics window system audio network REQUIRED)

find_package(PkgConfig QUIET)
if(PKG_CONFIG_FOUND)
    pkg_check_modules(TMXLITE QUIET IMPORTED_TARGET tmxlite)
endif()

if(NOT TARGET PkgConfig::TMXLITE)
    find_package(tmxlite QUIET CONFIG)
endif()

if(NOT TARGET PkgConfig::TMXLITE AND NOT TARGET tmxlite::tmxlite)
    message(FATAL_ERROR "
    tmxlite не найдена! Пожалуйста, установите библиотеку:
    - MacOS: brew install tmxlite
    - Linux: sudo apt install libtmxlite-dev  (или аналог)
    - Windows (MSYS): pacman -S mingw-w64-x86_64-tmxlite
    - Windows (vcpkg): vcpkg install tmxlite
    ")
endif()

get_target_property(SFML_DIR sfml-graphics INTERFACE_INCLUDE_DIRECTORIES)
string(REGEX REPLACE "/include.*" "" SFML_DIR "${SFML_DIR}")

file(GLOB_RECURSE SOURCES "src/*.cpp")
add_executable(${PROJECT_NAME} ${SOURCES})

target_include_directories(${PROJECT_NAME} PRIVATE src)

if(TARGET PkgConfig::TMXLITE)
    target_link_libraries(${PROJECT_NAME} 
        sfml-graphics
        sfml-window
        sfml-system
        sfml-audio
        sfml-network
        PkgConfig::TMXLITE
    )
elseif(TARGET tmxlite::tmxlite)
    target_link_libraries(${PROJECT_NAME} 
        sfml-graphics
        sfml-window
        sfml-system
        sfml-audio
        sfml-network
        tmxlite::tmxlite
    )
endif()

if(WIN32)
    add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            ${SFML_DIR}/bin/libsfml-graphics-2.dll
            ${SFML_DIR}/bin/libsfml-window-2.dll
            ${SFML_DIR}/bin/libsfml-system-2.dll
            ${SFML_DIR}/bin/libsfml-audio-2.dll
            ${SFML_DIR}/bin/libsfml-network-2.dll
            $<TARGET_FILE_DIR:${PROJECT_NAME}>)
endif()