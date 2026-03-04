#include <SFML/Graphics.hpp>
#include <iostream>
#include <vector>

enum GameState {
    MENU,
    PLAYING
};

int main()
{
    // --- НАСТРОЙКИ РАЗРЕШЕНИЯ ---
    const int GAME_WIDTH = 640;
    const int GAME_HEIGHT = 640;
    const int SCALE = 1;
    const int WINDOW_WIDTH = GAME_WIDTH * SCALE;
    const int WINDOW_HEIGHT = GAME_HEIGHT * SCALE;

    // --- СОЗДАНИЕ ОКНА ---
    sf::RenderWindow window(
        sf::VideoMode(WINDOW_WIDTH, WINDOW_HEIGHT),
        "Game Menu (W/S Navigation)",
        sf::Style::Titlebar | sf::Style::Close
    );
    window.setVerticalSyncEnabled(true);

    // --- ВИД ---
    sf::View gameView(sf::FloatRect(0, 0, GAME_WIDTH, GAME_HEIGHT));
    window.setView(gameView);

    // --- ЗАГРУЗКА ШРИФТА ---
    sf::Font font;
    if (!font.loadFromFile("resources/fonts/arial.ttf"))
    {
        std::cerr << "Шрифт не найден, создаём меню без текста (но так не пойдёт!)" << std::endl;
        // На всякий случай создадим примитивный шрифт через загрузку системного
        font.loadFromFile("C:/Windows/Fonts/Arial.ttf"); // для Linux
        // Для Windows можно попробовать: "C:/Windows/Fonts/Arial.ttf"
    }

    // --- СОЗДАНИЕ КНОПОК ---
    struct MenuItem {
        sf::Text text;
        bool isSelected;
        std::string action; // "start" или "exit"
    };

    std::vector<MenuItem> menuItems;
    
    // Кнопка "Начать игру"
    MenuItem startItem;
    startItem.text.setFont(font);
    startItem.text.setString("Start Game");
    startItem.text.setCharacterSize(24);
    startItem.text.setPosition(220.f, 150.f);
    startItem.isSelected = true; // Первая кнопка выбрана по умолчанию
    startItem.action = "start";
    menuItems.push_back(startItem);
    
    // Кнопка "Выйти"
    MenuItem exitItem;
    exitItem.text.setFont(font);
    exitItem.text.setString("Exit");
    exitItem.text.setCharacterSize(24);
    exitItem.text.setPosition(220.f, 200.f);
    exitItem.isSelected = false;
    exitItem.action = "exit";
    menuItems.push_back(exitItem);

    // --- ЗАГОЛОВОК МЕНЮ ---
    sf::Text title;
    title.setFont(font);
    title.setString("MAIN MENU");
    title.setCharacterSize(36);
    title.setFillColor(sf::Color::Cyan);
    title.setPosition(200.f, 50.f);

    // --- ПЕРЕМЕННЫЕ ДЛЯ УПРАВЛЕНИЯ НАВИГАЦИЕЙ ---
    int selectedIndex = 0; // Индекс выбранного пункта меню (0 - Start, 1 - Exit)
    
    // Для защиты от слишком быстрого переключения (debouncing)
    sf::Clock navigationClock;
    const float NAVIGATION_COOLDOWN = 0.2f; // 200 мс между нажатиями

    // --- СОСТОЯНИЕ ИГРЫ ---
    GameState currentState = MENU;

    // --- ГЛАВНЫЙ ЦИКЛ ---
    while (window.isOpen())
    {
        // --- ОБРАБОТКА СОБЫТИЙ ---
        sf::Event event;
        while (window.pollEvent(event))
        {
            if (event.type == sf::Event::Closed)
                window.close();

            // Обработка только для состояния MENU
            if (currentState == MENU)
            {
                // --- НАВИГАЦИЯ ПО МЕНЮ (ТОЛЬКО W/S + ENTER) ---
                if (event.type == sf::Event::KeyPressed)
                {
                    // Защита от слишком быстрого нажатия (чтобы не пролистывать 10 кнопок за секунду)
                    if (navigationClock.getElapsedTime().asSeconds() < NAVIGATION_COOLDOWN)
                    {
                        // Пропускаем обработку, если не прошло достаточно времени
                        continue;
                    }
                    
                    // Навигация вверх (W)
                    if (event.key.code == sf::Keyboard::W)
                    {
                        // Сбрасываем выделение у текущей кнопки
                        menuItems[selectedIndex].isSelected = false;
                        
                        // Перемещаемся вверх (к предыдущей кнопке)
                        selectedIndex--;
                        if (selectedIndex < 0)
                        {
                            selectedIndex = menuItems.size() - 1; // Зацикливаем на последнюю
                        }
                        
                        // Выделяем новую кнопку
                        menuItems[selectedIndex].isSelected = true;
                        
                        // Сбрасываем таймер для защиты от быстрых нажатий
                        navigationClock.restart();
                        
                        std::cout << "IsSelected: " << selectedIndex << std::endl;
                    }
                    
                    // Навигация вниз (S)
                    if (event.key.code == sf::Keyboard::S)
                    {
                        menuItems[selectedIndex].isSelected = false;
                        
                        selectedIndex++;
                        if (selectedIndex >= menuItems.size())
                        {
                            selectedIndex = 0; // Зацикливаем на первую
                        }
                        
                        menuItems[selectedIndex].isSelected = true;
                        navigationClock.restart();
                        
                        std::cout << "IsSelected: " << selectedIndex << std::endl;
                    }
                    
                    // Выбор пункта меню (Enter)
                    if (event.key.code == sf::Keyboard::Enter)
                    {
                        if (menuItems[selectedIndex].action == "start")
                        {
                            std::cout << "Starting game!" << std::endl;
                            currentState = PLAYING;
                        }
                        else if (menuItems[selectedIndex].action == "exit")
                        {
                            std::cout << "Exiting(" << std::endl;
                            window.close();
                        }
                    }
                }
            }
            else if (currentState == PLAYING)
            {
                // В игре по Escape возвращаемся в меню
                if (event.type == sf::Event::KeyPressed && event.key.code == sf::Keyboard::Escape)
                {
                    currentState = MENU;
                    // Сбрасываем выделение на первый пункт при возврате в меню
                    for (auto& item : menuItems)
                    {
                        item.isSelected = false;
                    }
                    selectedIndex = 0;
                    menuItems[0].isSelected = true;
                }
            }
        }

        // --- ОБНОВЛЕНИЕ ЦВЕТОВ КНОПОК ---
        for (auto& item : menuItems)
        {
            if (item.isSelected)
            {
                item.text.setFillColor(sf::Color::Yellow); // Выбранный пункт - жёлтый
                // Можно добавить стрелочку или другой индикатор
            }
            else
            {
                item.text.setFillColor(sf::Color::White); // Обычный пункт - белый
            }
        }

        // --- ОТРИСОВКА ---
        window.clear(sf::Color::Black);
        
        if (currentState == MENU)
        {
            // Рисуем заголовок
            window.draw(title);
            
            // Рисуем кнопки меню
            for (const auto& item : menuItems)
            {
                window.draw(item.text);
            }
            
            // Добавляем визуальный индикатор выбранного пункта (стрелочку)
            if (selectedIndex >= 0 && selectedIndex < menuItems.size())
            {
                sf::Text arrow;
                arrow.setFont(font);
                arrow.setString(">");
                arrow.setCharacterSize(24);
                arrow.setFillColor(sf::Color::Yellow);
                
                // Позиционируем стрелочку слева от выбранного текста
                sf::FloatRect textBounds = menuItems[selectedIndex].text.getGlobalBounds();
                arrow.setPosition(textBounds.left - 30, textBounds.top);
                
                window.draw(arrow);
            }
            
            // Подсказка по управлению
            sf::Text hint;
            hint.setFont(font);
            hint.setString("W/S - navigate   Enter - select");
            hint.setCharacterSize(16);
            hint.setFillColor(sf::Color(150, 150, 150));
            hint.setPosition(180.f, 280.f);
            window.draw(hint);
        }
        else if (currentState == PLAYING)
        {
            // Простая игровая сцена для демонстрации
            sf::CircleShape player(20.f);
            player.setFillColor(sf::Color::Green);
            player.setPosition(300.f, 160.f);
            window.draw(player);
            
            sf::Text gameHint;
            gameHint.setFont(font);
            gameHint.setString("Game is running! Press ESC for menu");
            gameHint.setCharacterSize(16);
            gameHint.setFillColor(sf::Color::White);
            gameHint.setPosition(150.f, 300.f);
            window.draw(gameHint);
        }
        
        window.display();
    }

    return 0;
}