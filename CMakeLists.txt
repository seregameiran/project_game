cmake_minimum_required(VERSION 3.10)
project(SFML_Project)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(LIBS_DIR ${CMAKE_SOURCE_DIR}/libraries)

file(GLOB_RECURSE SOURCES "src/*.cpp")
add_executable(${PROJECT_NAME} ${SOURCES})

# Подключаем заголовки
target_include_directories(${PROJECT_NAME} PRIVATE 
    src
    ${LIBS_DIR}/SFML/include
    ${LIBS_DIR}/tmxlite/include
)

# Пути к библиотекам
target_link_directories(${PROJECT_NAME} PRIVATE
    ${LIBS_DIR}/SFML/lib
    ${LIBS_DIR}/tmxlite/lib
)

# Линковка (универсальные имена)
if(WIN32)
    target_link_libraries(${PROJECT_NAME}
        sfml-graphics.lib
        sfml-window.lib
        sfml-system.lib
        sfml-audio.lib
        sfml-network.lib
        tmxlite.lib
    )
elseif(APPLE)
    target_link_libraries(${PROJECT_NAME}
        sfml-graphics
        sfml-window
        sfml-system
        sfml-audio
        sfml-network
        tmxlite
    )
else()
    target_link_libraries(${PROJECT_NAME}
        sfml-graphics
        sfml-window
        sfml-system
        sfml-audio
        sfml-network
        tmxlite
    )
endif()

# Копирование библиотек
if(WIN32 AND EXISTS ${LIBS_DIR}/SFML/bin)
    # Windows: копируем DLL
    add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_directory
            ${LIBS_DIR}/SFML/bin
            $<TARGET_FILE_DIR:${PROJECT_NAME}>
        COMMENT "Копируем DLL для Windows..."
    )
    
    if(EXISTS ${LIBS_DIR}/tmxlite/bin)
        add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_directory
                ${LIBS_DIR}/tmxlite/bin
                $<TARGET_FILE_DIR:${PROJECT_NAME}>
            APPEND
        )
    endif()
    
elseif(APPLE)
    # macOS: создаём .app bundle и копируем .dylib
    set(APP_BUNDLE_DIR "${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}.app")
    set(APP_FRAMEWORKS_DIR "${APP_BUNDLE_DIR}/Contents/Frameworks")
    set(APP_EXECUTABLE "${APP_BUNDLE_DIR}/Contents/MacOS/${PROJECT_NAME}")
    
    # Создаём структуру .app
    add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E make_directory ${APP_FRAMEWORKS_DIR}
        COMMAND ${CMAKE_COMMAND} -E make_directory ${APP_BUNDLE_DIR}/Contents/MacOS
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            $<TARGET_FILE:${PROJECT_NAME}>
            ${APP_EXECUTABLE}
        COMMENT "Создаём .app bundle для macOS..."
    )
    
    # Копируем .dylib
    if(EXISTS ${LIBS_DIR}/SFML/lib)
        file(GLOB SFML_DYLIBS "${LIBS_DIR}/SFML/lib/*.dylib")
        if(SFML_DYLIBS)
            add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
                COMMAND ${CMAKE_COMMAND} -E copy_if_different
                    ${SFML_DYLIBS}
                    ${APP_FRAMEWORKS_DIR}/
                APPEND
            )
        endif()
    endif()
    
    if(EXISTS ${LIBS_DIR}/tmxlite/lib)
        file(GLOB TMXLITE_DYLIBS "${LIBS_DIR}/tmxlite/lib/*.dylib")
        if(TMXLITE_DYLIBS)
            add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
                COMMAND ${CMAKE_COMMAND} -E copy_if_different
                    ${TMXLITE_DYLIBS}
                    ${APP_FRAMEWORKS_DIR}/
                APPEND
            )
        endif()
    endif()
    
    # Правим пути (чтобы библиотеки находили друг друга)
    add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
        COMMAND install_name_tool -add_rpath "@executable_path/../Frameworks" ${APP_EXECUTABLE}
        COMMENT "Настраиваем rpath для macOS..."
        APPEND
    )
endif()