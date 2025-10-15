# 🚀 MOEX WebSocket Monitor

Production-ready мониторинг Московской биржи в реальном времени через WebSocket API.

## 📊 Возможности

- ✅ **30 параллельных WebSocket соединений**
- ✅ **1500 тикеров** (30 × 50 случайных из MOEX)
- ✅ **Обновляемый консольный вывод** (каждую секунду)
- ✅ **Время последнего обновления** для каждого тикера с цветовой индикацией
- ✅ **Автоматическое переподключение** при обрывах
- ✅ **Docker контейнер** готов к развертыванию

## 🏗️ Архитектура

```
30 WebSocket соединений (Python asyncio)
    ↓
wss://iss.moex.com/infocx/v3/websocket
    ↓
STOMP протокол
    ↓
1500 подписок на orderbooks
    ↓
Real-time console display
```

## 🚀 Быстрый старт

### Docker (Рекомендуется):

```bash
# Создайте .env файл
cp .env.example .env

# Запустите
docker-compose up
```

### Локально:

```bash
# Установите зависимости
pip install -r requirements.txt

# Создайте .env
cp .env.example .env

# Запустите
python3 monitor_1500.py
```

## 📋 Что отображается

```
==============================================================================================================
  MOEX Real-time Monitor - 1500 Tickers (30 Connections × 50 Each)
==============================================================================================================
Connections: 30/30 | Updates: 1234 | Tickers: 256/1500 | With Prices: 87 | Rate: 12.5 msg/s | Uptime: 98s

Ticker |      BID |      ASK |     LAST |       Volume |  Upd | Last Update
--------------------------------------------------------------------------------------------------------------
SBER   |   283.50 |   283.55 |   283.52 |    1,234,567 |   45 | 14:32:15  ← 🟢 < 5 сек
GAZP   |   115.20 |   115.25 |   115.22 |      987,654 |   42 | 14:32:10  ← 🟡 < 30 сек
LKOH   |  5840.00 |  5841.00 |  5840.50 |       12,345 |   38 | 14:31:50  ← 🔴 > 30 сек
...

Connections Status:
Online (30): 1, 2, 3, ... 30
```

### Цветовая индикация времени обновления:

- 🟢 **Зеленый** - обновление < 5 секунд (очень свежие данные)
- 🟡 **Желтый** - обновление < 30 секунд (свежие данные)
- 🔴 **Красный** - обновление > 30 секунд (устаревшие данные)

## 🔑 Конфигурация

Создайте файл `.env`:

```bash
MOEX_DOMAIN=DEMO
MOEX_LOGIN=guest
MOEX_PASSCODE=guest
```

**DEMO креденшелы** дают полный доступ к WebSocket API!

## ⏰ Когда запускать

**Торговая сессия MOEX**: Понедельник - Пятница, 10:00 - 18:40 МСК

Вне торговой сессии данные будут пустые (N/A).

## 📦 Зависимости

- Python 3.12+
- websockets
- python-dotenv

## 🐳 Docker Hub

Образ опубликован: **smith1984/moex-ws-monitor:latest**

```bash
docker pull smith1984/moex-ws-monitor:latest
docker run -it smith1984/moex-ws-monitor:latest
```

## 📁 Структура проекта

```
moex-ws-test/
├── monitor_1500.py       # Главный файл мониторинга ⭐
├── stomp_utils.py        # STOMP протокол
├── Dockerfile            # Docker образ
├── docker-compose.yml    # Docker Compose конфигурация
├── requirements.txt      # Python зависимости
├── .env.example          # Пример конфигурации
├── README.md            # Эта документация
├── FINAL_README.md      # Подробная документация
└── SERVER_INFO.md       # Информация о развертывании
```

## 🛑 Остановка

Нажмите `Ctrl+C` для graceful shutdown с финальной статистикой.

## 📝 Технические детали

- **WebSocket URL**: `wss://iss.moex.com/infocx/v3/websocket`
- **Протокол**: STOMP
- **Destination**: `MXSE.orderbooks`
- **Selector**: `TICKER="MXSE.TQBR.{ticker}"`
- **Ping интервал**: 20 секунд
- **Обновление дисплея**: 1 раз в секунду

## 🌐 Production сервер

Уже развернут на: **185.119.58.125**

```bash
ssh root@185.119.58.125
docker attach moex-ws-monitor
```

## 📄 Лицензия

MIT

---

**Готово к production использованию!** 🎊
