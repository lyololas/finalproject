import pygame
import sys
import random
import math
import sqlite3

pygame.init()

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
JUMP_STRENGTH = 10
PLAYER_WIDTH = 40
PLAYER_HEIGHT = 40
ENEMY_WIDTH = 50
ENEMY_HEIGHT = 50
ENEMY_SPEED = 2
BULLET_WIDTH = 5
BULLET_HEIGHT = 5
BULLET_SPEED = 10
PLANK_WIDTH = 100
PLANK_HEIGHT = 20

WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
BLACK = (0, 0, 0)
BROWN = (139, 69, 19)
GREEN = (0, 255, 0)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("help")


# SQLite Database Setup
def init_db():
    conn = sqlite3.connect('high_scores.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS scores
                 (id INTEGER PRIMARY KEY, score INTEGER)''')
    conn.commit()
    conn.close()

def save_score(score):
    conn = sqlite3.connect('high_scores.db')
    c = conn.cursor()
    c.execute("INSERT INTO scores (score) VALUES (?)", (score,))
    conn.commit()
    conn.close()

def get_high_score():
    conn = sqlite3.connect('high_scores.db')
    c = conn.cursor()
    c.execute("SELECT MAX(score) FROM scores")
    high_score = c.fetchone()[0]
    conn.close()
    return high_score if high_score else 0

init_db()

class Camera:
    def __init__(self, width, height):
        self.camera_rect = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height

    def apply(self, entity):
        return entity.rect.move(self.camera_rect.topleft)

    def update(self, target):
        x = -target.rect.centerx + SCREEN_WIDTH // 2
        y = -target.rect.centery + SCREEN_HEIGHT // 2

        x = min(0, x)
        y = min(0, y)
        x = max(-(self.width - SCREEN_WIDTH), x)
        y = max(-(self.height - SCREEN_HEIGHT), y)

        self.camera_rect = pygame.Rect(x, y, self.width, self.height)

class Player:
    def __init__(self, map_width):
        self.rect = pygame.Rect(100, SCREEN_HEIGHT - PLAYER_HEIGHT - 50, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.hitbox = pygame.Rect(PLAYER_WIDTH // 2, PLAYER_HEIGHT // 2, -1, -1)  # Хитбокс 10x10 пикселей
        self.velocity_y = 0
        self.on_ground = False
        self.direction = 1
        self.planks = 0
        self.map_width = map_width
        self.score = 0

        # Масштабирование спрайта
        self.sprite_scale = 2  # Увеличиваем спрайт в 2 раза
        self.sprite_width = PLAYER_WIDTH * self.sprite_scale
        self.sprite_height = PLAYER_HEIGHT * self.sprite_scale

        self.sprite_sheet = pygame.image.load("Snail2.png").convert_alpha()
        self.frame_width = self.sprite_sheet.get_width() // 3
        self.frame_height = self.sprite_sheet.get_height() // 4
        self.frames = []

        for row in range(4):
            frames_row = []
            for col in range(3):
                frame = self.sprite_sheet.subsurface(pygame.Rect(col * self.frame_width, row * self.frame_height,
                                                             self.frame_width, self.frame_height))
                # Масштабируем каждый кадр спрайта
                frame = pygame.transform.scale(frame, (self.sprite_width, self.sprite_height))
                frames_row.append(frame)
            self.frames.append(frames_row)

        self.current_frame = 0
        self.animation_speed = 0.2
        self.animation_time = 0
        self.current_direction = 0

        # Переменная для ограничения частоты выстрелов
        self.last_shot_time = 0
        self.shoot_cooldown = 200  # Задержка между выстрелами в миллисекундах

    def move(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy

        # Обновление позиции хитбокса (центр спрайта)
        self.hitbox.x = self.rect.x + (self.sprite_width - self.hitbox.width) // 2
        self.hitbox.y = self.rect.y + (self.sprite_height - self.hitbox.height) // 2

        if self.rect.x < 0:
            self.rect.x = 0
        elif self.rect.x > self.map_width - self.sprite_width:
            self.rect.x = self.map_width - self.sprite_width

        if self.rect.y < 0:
            self.rect.y = 0
        elif self.rect.y > SCREEN_HEIGHT - self.sprite_height:
            self.rect.y = SCREEN_HEIGHT - self.sprite_height

        if dx < 0:
            self.direction = -1
            self.current_direction = 1  # влево
        elif dx > 0:
            self.direction = 1
            self.current_direction = 2  # вправо

        if dy < 0:
            self.current_direction = 3  # вверх
        elif dy > 0:
            self.current_direction = 0  # вниз

    def update(self):
        self.rect.y += self.velocity_y

        if self.rect.y >= SCREEN_HEIGHT - self.sprite_height:
            self.rect.y = SCREEN_HEIGHT - self.sprite_height
            self.on_ground = True
            self.velocity_y = 0

        # Обновление позиции хитбокса
        self.hitbox.x = self.rect.x + (self.sprite_width - self.hitbox.width) // 2
        self.hitbox.y = self.rect.y + (self.sprite_height - self.hitbox.height) // 2

        self.animation_time += clock.get_time() / 1000
        if self.animation_time >= self.animation_speed:
            self.animation_time = 0
            self.current_frame = (self.current_frame + 1) % 3

    def draw(self, surface, camera):
        frame = self.frames[self.current_direction][self.current_frame]
        surface.blit(frame, camera.apply(self))



class Enemy:
    def __init__(self, x, y, player):
        self.sprite_scale = 2
        self.sprite_width = ENEMY_WIDTH * self.sprite_scale
        self.sprite_height = ENEMY_HEIGHT * self.sprite_scale

        self.rect = pygame.Rect(x, y, self.sprite_width, self.sprite_height)
        self.hitbox = pygame.Rect(x, y, self.sprite_width, self.sprite_height)  # Хитбокс по размеру врага
        self.player = player

        self.sprite_sheet = pygame.image.load("Frog.png").convert_alpha()
        self.frame_width = self.sprite_sheet.get_width() // 7
        self.frame_height = self.sprite_sheet.get_height()
        self.frames = []

        for col in range(7):
            frame = self.sprite_sheet.subsurface(pygame.Rect(col * self.frame_width, 0,
                                                             self.frame_width, self.frame_height))
            frame = pygame.transform.scale(frame, (self.sprite_width, self.sprite_height))
            self.frames.append(frame)

        self.current_frame = 0
        self.animation_speed = 0.2
        self.animation_time = 0

    def update(self):
        dx = self.player.rect.x - self.rect.x
        dy = self.player.rect.y - self.rect.y
        dist = math.hypot(dx, dy)
        if dist != 0:
            dx = dx / dist
            dy = dy / dist

        self.rect.x += dx * ENEMY_SPEED
        self.rect.y += dy * ENEMY_SPEED

        # Обновление позиции хитбокса
        self.hitbox.x = self.rect.x
        self.hitbox.y = self.rect.y

        self.animation_time += clock.get_time() / 1000
        if self.animation_time >= self.animation_speed:
            self.animation_time = 0
            self.current_frame = (self.current_frame + 1) % 7

    def draw(self, surface, camera):
        frame = self.frames[self.current_frame]
        surface.blit(frame, camera.apply(self))

class Bullet:
    def __init__(self, x, y, angle):
        # Начальные координаты пули — центр спрайта игрока
        self.rect = pygame.Rect(x - BULLET_WIDTH // 2, y - BULLET_HEIGHT // 2, BULLET_WIDTH, BULLET_HEIGHT)
        self.direction_x = math.cos(angle)
        self.direction_y = math.sin(angle)
        self.start_x = x
        self.start_y = y
        self.max_distance = 300

    def update(self):
        self.rect.x += BULLET_SPEED * self.direction_x
        self.rect.y += BULLET_SPEED * self.direction_y

        # Удаляем пулю, если она пролетела максимальное расстояние
        if abs(self.rect.x - self.start_x) > self.max_distance or abs(self.rect.y - self.start_y) > self.max_distance:
            return True
        return False

class Plank:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, PLANK_WIDTH, PLANK_HEIGHT)
        self.broken = False

    def draw(self, surface, camera):
        if not self.broken:
            pygame.draw.rect(surface, BROWN, camera.apply(self))

def menu():
    while True:
        
        screen.fill(WHITE)

        font = pygame.font.Font(None, 74)
        title_text = font.render("omegaylitka", True, BLACK)
        start_text = font.render("Начать", True, BLACK)
        exit_text = font.render("Выход", True, BLACK)
        high_score_text = font.render(f"High Score: {get_high_score()}", True, BLACK)

        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4))
        start_rect = start_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        exit_rect = exit_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
        high_score_rect = high_score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100))

        screen.blit(title_text, title_rect)
        screen.blit(start_text, start_rect)
        screen.blit(exit_text, exit_rect)
        screen.blit(high_score_text, high_score_rect)

        mouse_pos = pygame.mouse.get_pos()
        if start_rect.collidepoint(mouse_pos):
            start_text = font.render("Начать игру", True, BLACK)
            if pygame.mouse.get_pressed()[0]:
                return
        else:
            start_text = font.render("Начать игру", True, BLACK)

        if exit_rect.collidepoint(mouse_pos):
            exit_text = font.render("Выход", True, BLACK)
            if pygame.mouse.get_pressed()[0]:
                pygame.quit()
                sys.exit()
        else:
            exit_text = font.render("Выход", True, BLACK)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

def game_over_screen(score):
    save_score(score)
    while True:
        screen.fill(WHITE)

        font = pygame.font.Font(None, 74)
        game_over_text = font.render("Game Over", True, BLACK)
        score_text = font.render(f"Score: {score}", True, BLACK)
        retry_text = font.render("Retry", True, BLACK)
        exit_text = font.render("Exit", True, BLACK)

        game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4))
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        retry_rect = retry_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
        exit_rect = exit_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100))

        screen.blit(game_over_text, game_over_rect)
        screen.blit(score_text, score_rect)
        screen.blit(retry_text, retry_rect)
        screen.blit(exit_text, exit_rect)

        mouse_pos = pygame.mouse.get_pos()
        if retry_rect.collidepoint(mouse_pos):
            retry_text = font.render("Retry", True, BLACK)
            if pygame.mouse.get_pressed()[0]:
                return True
        else:
            retry_text = font.render("Retry", True, BLACK)

        if exit_rect.collidepoint(mouse_pos):
            exit_text = font.render("Exit", True, BLACK)
            if pygame.mouse.get_pressed()[0]:
                return False
        else:
            exit_text = font.render("Exit", True, BLACK)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
def you_won_screen(score):
    save_score(score)
    while True:
        screen.fill(WHITE)

        font = pygame.font.Font(None, 74)
        you_won_text = font.render("You Won!", True, BLACK)
        score_text = font.render(f"Final Score: {score}", True, BLACK)
        exit_text = font.render("Exit", True, BLACK)

        you_won_rect = you_won_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4))
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        exit_rect = exit_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100))

        screen.blit(you_won_text, you_won_rect)
        screen.blit(score_text, score_rect)
        screen.blit(exit_text, exit_rect)

        mouse_pos = pygame.mouse.get_pos()
        if exit_rect.collidepoint(mouse_pos):
            exit_text = font.render("Exit", True, BLACK)
            if pygame.mouse.get_pressed()[0]:
                return False
        else:
            exit_text = font.render("Exit", True, BLACK)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()



def load_map_image(filename, new_size):
    original_image = pygame.image.load(filename).convert()
    return pygame.transform.scale(original_image, new_size)

new_map_size = (1300, 600)
map_image = load_map_image("middle.png", new_map_size)


menu()
player = Player(new_map_size[0])
enemies = []
bullets = []


plank = Plank(300, SCREEN_HEIGHT - 100)
camera = Camera(new_map_size[0], new_map_size[1])

# В основном игровом цикле
player.draw(screen, camera)  # Отрисовка игрока

clock = pygame.time.Clock()
enemy_spawn_time = 0
notification = ""

# Добавляем переменные для таймера и уровня
level = 1
start_time = pygame.time.get_ticks()
level_transition = False
transition_start_time = 0

while True:
    current_time = pygame.time.get_ticks()
    elapsed_time = (current_time - start_time) // 1000  # Время в секундах

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    keys = pygame.key.get_pressed()
    if keys[pygame.K_a]:
        player.move(-5, 0)
    if keys[pygame.K_d]:
        player.move(5, 0)
    if keys[pygame.K_w]:
        player.move(0, -5)
    if keys[pygame.K_s]:
        player.move(0, 5)
    if keys[pygame.K_SPACE]:
        current_time = pygame.time.get_ticks()
        if current_time - player.last_shot_time > player.shoot_cooldown:
            center_x = player.rect.x + PLAYER_WIDTH // 2
            center_y = player.rect.y + PLAYER_HEIGHT // 2
            mouse_x, mouse_y = pygame.mouse.get_pos()
            angle = math.atan2(mouse_y - center_y, mouse_x - center_x)
            bullets.append(Bullet(center_x, center_y, angle))
            player.last_shot_time = current_time
    if keys[pygame.K_t]:
        if plank.rect.colliderect(player.rect) and not plank.broken:
            player.planks += 1
            plank.broken = True
            notification = "Вы собрали доску!"

    player.update()

    # Логика перехода на следующий уровень
    if level < 4 and elapsed_time >= 5 and not level_transition:
        level_transition = True
        transition_start_time = current_time

    if level_transition:
        if current_time - transition_start_time < 3000:  # 3 секунды черного экрана
            screen.fill(BLACK)
            font = pygame.font.Font(None, 74)
            level_text = font.render(f"Вы прошли уровень {level}!", True, WHITE)
            level_rect = level_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            screen.blit(level_text, level_rect)
            pygame.display.flip()
            continue
        else:
            level += 1
            level_transition = False
            start_time = pygame.time.get_ticks()  # Сброс таймера для следующего уровня
            enemies = []  # Очищаем врагов для нового уровня

    # Проверка на завершение игры (уровень 4)
    if level == 4 and elapsed_time >= 60:
        if you_won_screen(player.score):
            # Если игрок хочет сыграть снова, сбросить игру
            player = Player(new_map_size[0])
            enemies = []
            bullets = []
            plank = Plank(300, SCREEN_HEIGHT - 100)
            player.score = 0
            level = 1  # Сброс уровня
            start_time = pygame.time.get_ticks()  # Сброс таймера
        else:
            pygame.quit()
            sys.exit()

    enemy_spawn_time += clock.get_time()
    if enemy_spawn_time >= 1000:
        spawn_side = random.choice(["left", "right", "top", "bottom"])
        if spawn_side == "left":
            spawn_x = -ENEMY_WIDTH
            spawn_y = random.randint(0, SCREEN_HEIGHT - ENEMY_HEIGHT)
        elif spawn_side == "right":
            spawn_x = new_map_size[0]
            spawn_y = random.randint(0, SCREEN_HEIGHT - ENEMY_HEIGHT)
        elif spawn_side == "top":
            spawn_x = random.randint(0, SCREEN_WIDTH - ENEMY_WIDTH)
            spawn_y = -ENEMY_HEIGHT
        elif spawn_side == "bottom":
            spawn_x = random.randint(0, SCREEN_WIDTH - ENEMY_WIDTH)
            spawn_y = SCREEN_HEIGHT

        enemies.append(Enemy(spawn_x, spawn_y, player))
        enemy_spawn_time = 0

    for enemy in enemies:
        enemy.update()

    for bullet in bullets[:]:
        if bullet.update():
            bullets.remove(bullet)
            continue
        for enemy in enemies[:]:
            if bullet.rect.colliderect(enemy.hitbox):
                enemies.remove(enemy)
                if bullet in bullets:
                    bullets.remove(bullet)
                    player.score += 1
                    break

    for enemy in enemies:
        if player.hitbox.colliderect(enemy.hitbox):
            if game_over_screen(player.score):
                player = Player(new_map_size[0])
                enemies = []
                bullets = []
                plank = Plank(300, SCREEN_HEIGHT - 100)
                player.score = 0
                level = 1  # Сброс уровня при проигрыше
                start_time = pygame.time.get_ticks()  # Сброс таймера
            else:
                pygame.quit()
                sys.exit()

    screen.fill(WHITE)
    screen.blit(map_image, (0, 0))

    camera.update(player)

    screen.blit(map_image, camera.camera_rect.topleft)

    player.draw(screen, camera)

    plank.draw(screen, camera)
    for enemy in enemies:
        enemy.draw(screen, camera)

    for bullet in bullets:
        pygame.draw.rect(screen, BLACK, camera.apply(bullet))

    if notification:
        font = pygame.font.Font(None, 36)
        notification_text = font.render(notification, True, BLACK)
        screen.blit(notification_text, (SCREEN_WIDTH // 2 - notification_text.get_width() // 2, SCREEN_HEIGHT // 2))
        notification = ""

    # Отображение таймера
    font = pygame.font.Font(None, 36)
    timer_text = font.render(f"Time: {60 - elapsed_time}", True, BLACK)
    screen.blit(timer_text, (SCREEN_WIDTH - 150, 10))

    font = pygame.font.Font(None, 36)
    score_text = font.render(f"Score: {player.score}", True, BLACK)
    screen.blit(score_text, (10, 10))

    pygame.display.flip()
    clock.tick(60)