cmake_minimum_required(VERSION 3.10)
project(SFML_Project)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(SFML 2.6 COMPONENTS graphics window system audio network REQUIRED)

add_executable(${PROJECT_NAME} main.cpp)

target_link_libraries(${PROJECT_NAME} 
    sfml-graphics
    sfml-window
    sfml-system
    sfml-audio
    sfml-network
)

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