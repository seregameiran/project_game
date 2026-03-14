#include <SFML/Graphics.hpp>
#include <tmxlite/Map.hpp>
#include <tmxlite/Layer.hpp>
#include <tmxlite/TileLayer.hpp>
#include <tmxlite/ObjectGroup.hpp>
#include <iostream>
#include <vector>
#include <memory>
#include <cmath>
#include <string>
#include <fstream>
#include <filesystem>
#include <map>

namespace fs = std::filesystem;

class TestGame {
private:
    sf::RenderWindow& window;
    sf::RectangleShape player;
    float playerSpeed = 200.0f;
    sf::View cameraView;
    
    // Данные карты
    tmx::Map map;
    std::vector<sf::Texture> tileTextures;
    std::vector<sf::Sprite> tileSprites;  // Все спрайты в одном векторе для быстрой отрисовки
    std::vector<std::vector<bool>> collisionMap;

    // Размеры тайлов для каждого тайлсета
    std::vector<sf::Vector2u> tilesetTileSizes;

    // Анимированная вода
    struct WaterSpriteInfo
    {
        std::size_t spriteIndex;
        std::size_t tilesetIndex;
    };
    std::vector<WaterSpriteInfo> waterSprites;
    float waterAnimTime = 0.f;
    
    int mapWidth = 0;
    int mapHeight = 0;
    int tileSize = 0;
    
    // Объекты на карте
    std::vector<sf::FloatRect> collisionObjects;
    std::vector<sf::Vector2f> spawnPoints;
    
    // Для отладки
    sf::Font debugFont;
    sf::Text debugText;
    bool showDebug = false; // по умолчанию без подсветки коллизий
    int spriteCount = 0;

public:
    TestGame(sf::RenderWindow& win) : window(win) {
        player.setSize(sf::Vector2f(32, 32));
        player.setFillColor(sf::Color::Green);
        player.setPosition(100, 100);

        cameraView = window.getDefaultView();
        // Приближаем камеру, сохраняя пропорции (без растяжения)
        {
            const float zoomFactor = 0.75f; // чем меньше, тем сильнее приближение
            sf::Vector2f viewSize = cameraView.getSize();
            cameraView.setSize(viewSize.x * zoomFactor, viewSize.y * zoomFactor);
        }
        
        // Загружаем шрифт для отладки
        if (std::filesystem::exists("D:/project_game/assets/fonts/arial.ttf")) {
            if (debugFont.loadFromFile("D:/project_game/assets/fonts/arial.ttf")) {
                debugText.setFont(debugFont);
                debugText.setCharacterSize(18);
                debugText.setFillColor(sf::Color::White);
                debugText.setPosition(10, 10);
            }
        }
    }
    
    bool loadMap(const std::string& filename) {
        if (!map.load(filename)) {
            std::cerr << "Не удалось загрузить карту: " << filename << std::endl;
            return false;
        }
        
        // Получаем размеры карты
        auto bounds = map.getBounds();
        tileSize = map.getTileSize().x;
        mapWidth = bounds.width / tileSize;
        mapHeight = bounds.height / tileSize;
        
        std::cout << "Карта загружена: " << mapWidth << "x" << mapHeight 
                  << ", размер тайла: " << tileSize << "px" << std::endl;
        
        // Информация о слоях
        std::cout << "Слои карты:" << std::endl;
        for (const auto& layer : map.getLayers()) {
            std::cout << " - Слой: " << layer->getName() 
                      << ", тип: " << (int)layer->getType() 
                      << ", видимость: " << layer->getVisible() << std::endl;
        }
        
        // Загружаем текстуры тайлов
        const auto& tilesets = map.getTilesets();
        tileTextures.resize(tilesets.size());
        tilesetTileSizes.resize(tilesets.size());

        // Путь к папке с текстурами
        std::string texturesPath = "D:/project_game/assets/";

        for (size_t i = 0; i < tilesets.size(); ++i) {
            const auto& ts = tilesets[i];

            // Запоминаем размер тайла этого тайлсета
            tilesetTileSizes[i] = sf::Vector2u(
                static_cast<unsigned>(ts.getTileSize().x),
                static_cast<unsigned>(ts.getTileSize().y)
            );
            
            // Получаем путь из тайлсета
            std::string imagePath = ts.getImagePath();
            
            std::cout << "Исходный путь из тайлсета " << i << ": " << imagePath << std::endl;
            
            // Извлекаем только имя файла
            size_t lastSlash = imagePath.find_last_of("/\\");
            if (lastSlash != std::string::npos) {
                imagePath = imagePath.substr(lastSlash + 1);
            }
            
            // Приводим к нижнему регистру для поиска
            std::string lowerPath = imagePath;
            std::transform(lowerPath.begin(), lowerPath.end(), lowerPath.begin(), ::tolower);
            
            // Проверяем, нужно ли добавить -1
            std::string actualPath = imagePath;
            size_t dotPos = imagePath.find_last_of('.');
            
            // Список возможных файлов
            std::vector<std::string> possiblePaths;
            
            // Вариант 1: как есть
            possiblePaths.push_back(texturesPath + imagePath);
            
            // Вариант 2: с -1 перед расширением
            if (dotPos != std::string::npos) {
                std::string withDash = imagePath.substr(0, dotPos) + imagePath.substr(dotPos);
                possiblePaths.push_back(texturesPath + withDash);
                
                // Вариант 3: с маленькой буквы
                std::string lowerWithDash = withDash;
                std::transform(lowerWithDash.begin(), lowerWithDash.end(), lowerWithDash.begin(), ::tolower);
                possiblePaths.push_back(texturesPath + lowerWithDash);
            }
            
            // Пробуем загрузить
            bool loaded = false;
            for (const auto& path : possiblePaths) {
                std::cout << "Пробуем: " << path << std::endl;
                if (std::filesystem::exists(path)) {
                    if (tileTextures[i].loadFromFile(path)) {
                        std::cout << "Загружена текстура: " << path 
                                  << ", размер: " << tileTextures[i].getSize().x << "x" 
                                  << tileTextures[i].getSize().y << std::endl;
                        loaded = true;
                        break;
                    }
                }
            }
            
            if (!loaded) {
                std::cerr << "Не удалось загрузить текстуру для тайлсета " << i << std::endl;
                return false;
            }
        }
        
        // Создаём спрайты для всех тайлов
        tileSprites.clear();
        collisionMap.clear();
        collisionMap.resize(mapHeight, std::vector<bool>(mapWidth, false));
        waterSprites.clear();
        
        // Проходим по всем тайловым слоям
        const auto& layers = map.getLayers();
        for (const auto& layer : layers) {
            if (layer->getType() == tmx::Layer::Type::Tile && layer->getVisible()) {
                const auto& tileLayer = dynamic_cast<const tmx::TileLayer&>(*layer);
                const auto& tiles = tileLayer.getTiles();
                
                std::cout << "Обработка слоя: " << layer->getName() << std::endl;
                
                for (int y = 0; y < mapHeight; ++y) {
                    for (int x = 0; x < mapWidth; ++x) {
                        int idx = y * mapWidth + x;
                        if (idx >= tiles.size()) continue;
                        
                        const auto& tile = tiles[idx];
                        if (tile.ID == 0) continue;
                        
                        // Находим нужный тайлсет
                        for (const auto& ts : map.getTilesets()) {
                            if (tile.ID >= ts.getFirstGID() && 
                                tile.ID < ts.getFirstGID() + ts.getTileCount()) {
                                
                                int localID = tile.ID - ts.getFirstGID();
                                int tsIndex = &ts - &map.getTilesets()[0];
                                
                                auto& tex = tileTextures[tsIndex];
                                auto tsTileSize = tilesetTileSizes[tsIndex];
                                int texWidth = tex.getSize().x / static_cast<int>(tsTileSize.x);
                                
                                int tx = localID % texWidth;
                                int ty = localID / texWidth;
                                
                                sf::Sprite sprite;
                                sprite.setTexture(tex);
                                sprite.setTextureRect(sf::IntRect(
                                    tx * static_cast<int>(tsTileSize.x),
                                    ty * static_cast<int>(tsTileSize.y),
                                    static_cast<int>(tsTileSize.x),
                                    static_cast<int>(tsTileSize.y)));
                                sprite.setPosition(x * tileSize, y * tileSize);
                                
                                tileSprites.push_back(sprite);
                                spriteCount++;

                                // Запоминаем водные тайлы для последующей анимации.
                                // В tileset Ground вода — это анимированный тайл 5/6,
                                // поэтому считаем водой локальные ID 5 и 6.
                                if (ts.getName() == "Ground" &&
                                    (localID == 5u || localID == 6u))
                                {
                                    WaterSpriteInfo info;
                                    info.spriteIndex = tileSprites.size() - 1;
                                    info.tilesetIndex = static_cast<std::size_t>(tsIndex);
                                    waterSprites.push_back(info);
                                }
                                break;
                            }
                        }
                    }
                }
            }
            
            // Загружаем объекты из слоёв объектов
            if (layer->getType() == tmx::Layer::Type::Object) {
                const auto& objectGroup = dynamic_cast<const tmx::ObjectGroup&>(*layer);
                std::cout << "Слой объектов: " << layer->getName() 
                          << ", объектов: " << objectGroup.getObjects().size() << std::endl;
                
                for (const auto& obj : objectGroup.getObjects()) {
                    // Спрайт для объектов, у которых есть tileID (деревья, отбойник, остановка и т.п.)
                    if (obj.getTileID() != 0) {
                        std::uint32_t gid = obj.getTileID();
                        // Сбрасываем биты флагов поворота/отражения, оставляем только ID тайла
                        gid &= 0x1FFFFFFF;

                        for (std::size_t i = 0; i < map.getTilesets().size(); ++i) {
                            const auto& ts = map.getTilesets()[i];
                            if (gid >= ts.getFirstGID() && gid < ts.getFirstGID() + ts.getTileCount()) {
                                std::uint32_t localID = gid - ts.getFirstGID();
                                auto& tex = tileTextures[i];
                                auto tsTileSize = tilesetTileSizes[i];

                                int texWidth = tex.getSize().x / static_cast<int>(tsTileSize.x);
                                int tx = static_cast<int>(localID % texWidth);
                                int ty = static_cast<int>(localID / texWidth);

                                sf::Sprite sprite;
                                sprite.setTexture(tex);
                                sprite.setTextureRect(sf::IntRect(
                                    tx * static_cast<int>(tsTileSize.x),
                                    ty * static_cast<int>(tsTileSize.y),
                                    static_cast<int>(tsTileSize.x),
                                    static_cast<int>(tsTileSize.y)));

                                // В Tiled объекты с tileID позиционируются по нижней части,
                                // поэтому поднимаем на высоту тайла
                                auto tmxPos = obj.getPosition();
                                sf::Vector2f pos(static_cast<float>(tmxPos.x), static_cast<float>(tmxPos.y));
                                pos.y -= static_cast<float>(tsTileSize.y);
                                sprite.setPosition(pos);

                                tileSprites.push_back(sprite);
                                spriteCount++;

                                // Решаем, должен ли этот объект иметь коллизию
                                bool solid = false;

                                // Отбойник и мусорка из тайлсета Decorations:
                                // gid 14 и 15 -> localID 3 и 4 (firstgid = 11)
                                if (ts.getName() == "Decorations" &&
                                    (localID == 3 || localID == 4))
                                {
                                    solid = true;
                                }

                                // Остановка из тайлсета Bus Station (единственный тайл)
                                if (ts.getName() == "Bus Station")
                                {
                                    solid = true;
                                }

                                if (solid)
                                {
                                    sf::FloatRect aabb(
                                        pos.x,
                                        pos.y,
                                        static_cast<float>(tsTileSize.x),
                                        static_cast<float>(tsTileSize.y));
                                    collisionObjects.push_back(aabb);
                                }

                                break;
                            }
                        }
                    }

                    // Получаем прямоугольник объекта (для обычных прямоугольных областей)
                    sf::FloatRect objRect(
                        obj.getPosition().x,
                        obj.getPosition().y,
                        obj.getAABB().width,
                        obj.getAABB().height
                    );
                    
                    // Если объект имеет тип "collision" или слой так называется — добавляем в коллизии
                    if (obj.getType() == "collision" || layer->getName() == "Collision") {
                        collisionObjects.push_back(objRect);
                        std::cout << "  Добавлена коллизия: " 
                                  << objRect.left << "," << objRect.top 
                                  << " " << objRect.width << "x" << objRect.height << std::endl;
                    }
                    
                    // Если объект имеет тип "spawn", это точка появления
                    if (obj.getType() == "spawn" || obj.getName() == "player_spawn") {
                        spawnPoints.push_back(sf::Vector2f(obj.getPosition().x, obj.getPosition().y));
                        std::cout << "  Точка появления: " 
                                  << obj.getPosition().x << "," << obj.getPosition().y << std::endl;
                    }
                }
            }
        }
        
        // Если есть точка появления, ставим игрока туда
        if (!spawnPoints.empty()) {
            player.setPosition(spawnPoints[0]);
            std::cout << "Игрок установлен на точку появления" << std::endl;
        }
        else {
            // Иначе ставим игрока в центр карты
            float startX = mapWidth * tileSize * 0.5f - player.getSize().x * 0.5f;
            float startY = mapHeight * tileSize * 0.5f - player.getSize().y * 0.5f;
            player.setPosition(startX, startY);
        }
        
        std::cout << "Всего загружено спрайтов: " << spriteCount << std::endl;
        std::cout << "Всего объектов коллизий: " << collisionObjects.size() << std::endl;
        
        return true;
    }
    
    void handleEvents() {
        sf::Event event;
        while (window.pollEvent(event)) {
            if (event.type == sf::Event::Closed)
                window.close();
            if (event.type == sf::Event::KeyPressed) {
                if (event.key.code == sf::Keyboard::F1) {
                    showDebug = !showDebug;
                }
            }
        }
    }
    
    void update(float deltaTime) {
        sf::Vector2f movement(0, 0);
        
        if (sf::Keyboard::isKeyPressed(sf::Keyboard::W)) movement.y -= 1;
        if (sf::Keyboard::isKeyPressed(sf::Keyboard::S)) movement.y += 1;
        if (sf::Keyboard::isKeyPressed(sf::Keyboard::A)) movement.x -= 1;
        if (sf::Keyboard::isKeyPressed(sf::Keyboard::D)) movement.x += 1;
        
        // Нормализация диагонального движения
        float len = std::sqrt(movement.x * movement.x + movement.y * movement.y);
        if (len > 0) {
            movement /= len;
            movement *= playerSpeed * deltaTime;
        }
        
        // Проверка коллизий с объектами
        sf::Vector2f newPos = player.getPosition() + movement;
        sf::FloatRect playerBounds(newPos.x, newPos.y, 32, 32);
        
        bool canMove = true;
        for (const auto& obj : collisionObjects) {
            if (playerBounds.intersects(obj)) {
                canMove = false;
                break;
            }
        }
        
        // Также проверяем границы карты
        if (newPos.x < 0 || newPos.x > mapWidth * tileSize - 32 ||
            newPos.y < 0 || newPos.y > mapHeight * tileSize - 32) {
            canMove = false;
        }
        
        if (canMove) {
            player.setPosition(newPos);
        }

        // Анимация воды (переключаем 2 кадра 5/6 из тайлсета Ground)
        if (!waterSprites.empty()) {
            waterAnimTime += deltaTime;
            // Полный цикл 1 секунда: 0.5 c кадр A, 0.5 c кадр B
            float phase = std::fmod(waterAnimTime, 1.0f);
            std::uint32_t frameLocalID = (phase < 0.5f) ? 5u : 6u;

            for (const auto& info : waterSprites) {
                auto& sprite = tileSprites[info.spriteIndex];
                auto tsTileSize = tilesetTileSizes[info.tilesetIndex];
                auto& tex = tileTextures[info.tilesetIndex];

                int texWidth = tex.getSize().x / static_cast<int>(tsTileSize.x);
                int tx = static_cast<int>(frameLocalID % texWidth);
                int ty = static_cast<int>(frameLocalID / texWidth);

                sprite.setTextureRect(sf::IntRect(
                    tx * static_cast<int>(tsTileSize.x),
                    ty * static_cast<int>(tsTileSize.y),
                    static_cast<int>(tsTileSize.x),
                    static_cast<int>(tsTileSize.y)));
            }
        }

        // Обновляем камеру, чтобы она следила за игроком
        sf::Vector2f center = player.getPosition();
        center.x += player.getSize().x / 2.f;
        center.y += player.getSize().y / 2.f;

        float worldWidth = static_cast<float>(mapWidth * tileSize);
        float worldHeight = static_cast<float>(mapHeight * tileSize);

        sf::Vector2f viewSize = cameraView.getSize();
        float halfViewW = viewSize.x / 2.f;
        float halfViewH = viewSize.y / 2.f;

        // Ограничиваем камеру границами карты по X
        if (worldWidth <= viewSize.x) {
            center.x = worldWidth / 2.f;
        } else {
            if (center.x < halfViewW) center.x = halfViewW;
            if (center.x > worldWidth - halfViewW) center.x = worldWidth - halfViewW;
        }

        // И по Y (для вертикальной прокрутки)
        if (worldHeight <= viewSize.y) {
            center.y = worldHeight / 2.f;
        } else {
            if (center.y < halfViewH) center.y = halfViewH;
            if (center.y > worldHeight - halfViewH) center.y = worldHeight - halfViewH;
        }

        cameraView.setCenter(center);
    }
    
    void draw() {
        window.clear(sf::Color::Black);  // Чёрный фон вместо синего

        // Сначала рисуем мир в камере
        window.setView(cameraView);
        
        // Отрисовка всех спрайтов карты
        for (const auto& sprite : tileSprites) {
            window.draw(sprite);
        }
        
        // Отрисовка коллизий для отладки
        if (showDebug) {
            for (const auto& obj : collisionObjects) {
                sf::RectangleShape rect(sf::Vector2f(obj.width, obj.height));
                rect.setPosition(obj.left, obj.top);
                rect.setFillColor(sf::Color(255, 0, 0, 50));  // Полупрозрачный красный
                rect.setOutlineColor(sf::Color::Red);
                rect.setOutlineThickness(1);
                window.draw(rect);
            }
        }
        
        // Отрисовка игрока
        window.draw(player);
        
        // Отладочную информацию рисуем в экранных координатах
        if (showDebug && debugFont.getInfo().family != "") {
            window.setView(window.getDefaultView());
            std::string debugStr = "Позиция: " + std::to_string((int)player.getPosition().x) + ", " + std::to_string((int)player.getPosition().y) + "\n";
            debugStr += "Спрайтов: " + std::to_string(spriteCount) + "\n";
            debugStr += "Коллизий: " + std::to_string(collisionObjects.size()) + "\n";
            debugStr += "F1: показать/скрыть отладку";
            debugText.setString(debugStr);
            window.draw(debugText);
        }
        
        window.display();
    }
};

int main() {
    sf::RenderWindow window(sf::VideoMode(800, 608), "TMXLite Test");
    
    TestGame game(window);
    
    // Абсолютный путь к карте
    std::string mapPath = "D:/project_game/assets/maps/location1.tmx";
    std::cout << "Загрузка карты: " << mapPath << std::endl;
    
    if (!game.loadMap(mapPath)) {
        std::cerr << "Не удалось загрузить карту!" << std::endl;
        return -1;
    }
    
    sf::Clock clock;
    
    while (window.isOpen()) {
        float deltaTime = clock.restart().asSeconds();
        
        game.handleEvents();
        game.update(deltaTime);
        game.draw();
    }
    
    return 0;
}