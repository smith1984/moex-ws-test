#!/usr/bin/env python3
"""
MOEX 30 WebSocket Monitor - 1500 Tickers Real-time
30 соединений × 50 тикеров = 1500 тикеров с обновляемым выводом в консоль
"""
import asyncio
import json
import os
import urllib.request
import signal
import random
import sys
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
from websockets import connect, ConnectionClosed
try:
    from stomp.utils import Frame, convert_frame, parse_frame
except ImportError:
    from stomp_utils import Frame, convert_frame, parse_frame

load_dotenv()

# Режимы диагностики и конфигурации через переменные окружения
DEBUG_FRAMES = os.getenv('DEBUG_FRAMES', '0') == '1'
SUB_SELECTOR_MODE = os.getenv('SUB_SELECTOR', 'TICKER').upper()  # TICKER | SECID | AUTO
MOEX_WS_URL = os.getenv('MOEX_URL', 'wss://iss.moex.com/infocx/v3/websocket')

# Цвета
C = type('C', (), {
    'G': '\033[92m', 'R': '\033[91m', 'Y': '\033[93m', 'B': '\033[94m',
    'C': '\033[96m', 'M': '\033[95m', 'BOLD': '\033[1m', 'END': '\033[0m',
    'CLEAR': '\033[2J', 'HOME': '\033[H'
})()


class TickerData:
    """Данные одного тикера"""
    def __init__(self, ticker):
        self.ticker = ticker
        self.bid = None
        self.offer = None
        self.last = None
        self.volume = None
        self.updates = 0
        self.last_update = None
    
    def update(self, data):
        self.bid = data.get('BID')
        self.offer = data.get('OFFER')
        self.last = data.get('LAST')
        self.volume = data.get('VOLTODAY')
        self.updates += 1
        self.last_update = datetime.now()
    
    def format_line(self):
        """Форматирует строку для вывода"""
        bid_str = f"{self.bid:>8.2f}" if self.bid else "     N/A"
        offer_str = f"{self.offer:>8.2f}" if self.offer else "     N/A"
        last_str = f"{self.last:>8.2f}" if self.last else "     N/A"
        vol_str = f"{self.volume:>12,}" if self.volume else "         N/A"
        
        # Время последнего обновления
        if self.last_update:
            time_str = self.last_update.strftime('%H:%M:%S')
            # Цвет в зависимости от свежести данных
            seconds_ago = (datetime.now() - self.last_update).seconds
            if seconds_ago < 5:
                time_color = C.G  # Зеленый - свежие данные
            elif seconds_ago < 30:
                time_color = C.Y  # Желтый - относительно свежие
            else:
                time_color = C.R  # Красный - устаревшие
        else:
            time_str = "  N/A   "
            time_color = C.END
        
        # Цвет для изменения
        change_color = C.END
        if self.bid and self.offer:
            if self.bid > self.offer * 0.99:
                change_color = C.G
        
        return (f"{self.ticker:6s} | "
                f"{C.G}{bid_str}{C.END} | "
                f"{C.R}{offer_str}{C.END} | "
                f"{C.C}{last_str}{C.END} | "
                f"{vol_str} | "
                f"{change_color}{self.updates:4d}{C.END} | "
                f"{time_color}{time_str}{C.END}")


class GlobalMonitor:
    """Глобальный монитор всех тикеров"""
    def __init__(self):
        self.tickers = {}  # {ticker: TickerData}
        self.conn_status = {}  # {conn_id: status}
        self.total_updates = 0
        self.start_time = datetime.now()
        self.lock = asyncio.Lock()
        self._debug_msg_count_by_conn = defaultdict(int)
    
    async def update_ticker(self, conn_id, ticker, data):
        async with self.lock:
            if ticker not in self.tickers:
                self.tickers[ticker] = TickerData(ticker)
            
            self.tickers[ticker].update(data)
            self.total_updates += 1
            
            if conn_id not in self.conn_status:
                self.conn_status[conn_id] = 'online'
    
    def set_conn_status(self, conn_id, status):
        self.conn_status[conn_id] = status

    def get_summary(self):
        uptime = (datetime.now() - self.start_time).seconds
        with_prices = sum(1 for t in self.tickers.values() if t.last)
        active_conns = sum(1 for s in self.conn_status.values() if s == 'online')
        return {
            'uptime': uptime,
            'total_messages': self.total_updates,
            'unique_tickers': len(self.tickers),
            'with_prices': with_prices,
            'rate': self.total_updates / uptime if uptime > 0 else 0.0,
            'connections_active': active_conns,
            'connections_total': len(self.conn_status) or 0,
        }
    
    def display_live(self):
        """Обновляемый вывод в консоль"""
        # Очистка экрана и возврат курсора
        print(f"{C.CLEAR}{C.HOME}", end='')
        
        uptime = (datetime.now() - self.start_time).seconds
        rate = self.total_updates / uptime if uptime > 0 else 0
        
        # Заголовок
        print(f"{C.BOLD}{C.C}{'='*110}")
        print(f"  MOEX Real-time Monitor - 1500 Tickers (30 Connections × 50 Each)")
        print(f"{'='*110}{C.END}")
        
        # Статусная строка
        active_conns = sum(1 for s in self.conn_status.values() if s == 'online')
        with_data = len(self.tickers)
        with_prices = sum(1 for t in self.tickers.values() if t.last)
        
        print(f"{C.G}Connections: {active_conns}/30{C.END} | "
              f"{C.C}Updates: {self.total_updates}{C.END} | "
              f"{C.M}Tickers: {with_data}/1500{C.END} | "
              f"{C.Y}With Prices: {with_prices}{C.END} | "
              f"{C.B}Rate: {rate:.1f} msg/s{C.END} | "
              f"Uptime: {uptime}s")
        
        print(f"\n{C.BOLD}{'Ticker':<6} | {'BID':>8} | {'ASK':>8} | {'LAST':>8} | {'Volume':>12} | {'Upd':>4} | {'Last Update':>8}{C.END}")
        print('-' * 110)
        
        # Сортируем тикеры по активности
        sorted_tickers = sorted(
            self.tickers.values(),
            key=lambda t: t.updates,
            reverse=True
        )
        
        # Показываем топ-50 (чтобы уместилось на экране)
        display_count = min(50, len(sorted_tickers))
        
        for ticker_data in sorted_tickers[:display_count]:
            print(ticker_data.format_line())
        
        if len(sorted_tickers) > display_count:
            print(f"\n{C.Y}... и еще {len(sorted_tickers) - display_count} тикеров{C.END}")
        elif not sorted_tickers:
            print(f"{C.Y}(Нет данных. Возможные причины: закрыта сессия, нет прав, неверный selector){C.END}")
        
        # Статистика по соединениям (компактно)
        print(f"\n{C.BOLD}Connections Status:{C.END}")
        online = [cid for cid, s in self.conn_status.items() if s == 'online']
        if online:
            online_str = ', '.join(f"{C.G}{cid}{C.END}" for cid in sorted(online)[:30])
            print(f"Online ({len(online)}): {online_str}")
        
        offline = [cid for cid, s in self.conn_status.items() if s != 'online']
        if offline:
            offline_str = ', '.join(f"{C.R}{cid}({self.conn_status[cid][:10]}){C.END}" for cid in sorted(offline)[:10])
            print(f"Issues ({len(offline)}): {offline_str}")
        
        print(f"\n{C.Y}Press Ctrl+C to stop{C.END}")


async def display_loop(monitor, stop):
    """Цикл обновления дисплея"""
    while not stop.is_set():
        monitor.display_live()
        await asyncio.sleep(1)  # Обновление каждую секунду
        # Автодиагностика: если долго нет апдейтов при онлайн-соединениях — подсказка
        if monitor.total_updates == 0 and any(s == 'online' for s in monitor.conn_status.values()):
            print(f"{C.Y}Подсказка: если данные не идут, проверьте переменные MOEX_DOMAIN/LOGIN/PASSCODE и SUB_SELECTOR{C.END}")


async def send_frame(ws, cmd, headers):
    await ws.send(b''.join(convert_frame(Frame(cmd, headers=headers))))


async def recv_frame(ws):
    return parse_frame(await ws.recv())


async def websocket_client(conn_id, tickers, monitor, stop):
    """WebSocket клиент для одного соединения"""
    url = MOEX_WS_URL
    domain = os.getenv('MOEX_DOMAIN', 'DEMO')
    login = os.getenv('MOEX_LOGIN', 'guest')
    passcode = os.getenv('MOEX_PASSCODE', 'guest')
    
    reconnect_delay = 5
    
    while not stop.is_set():
        try:
            monitor.set_conn_status(conn_id, 'connecting')
            
            async with connect(url, subprotocols=['STOMP'], ping_interval=20, ping_timeout=10) as ws:
                # CONNECT
                await send_frame(ws, 'CONNECT', {
                    'domain': domain,
                    'login': login,
                    'passcode': passcode
                })
                
                frame = await recv_frame(ws)
                if frame.cmd != 'CONNECTED':
                    monitor.set_conn_status(conn_id, 'auth_fail')
                    await asyncio.sleep(reconnect_delay)
                    continue
                
                # SUBSCRIBE
                for ticker in tickers:
                    if SUB_SELECTOR_MODE in ('TICKER', 'AUTO'):
                        await send_frame(ws, 'SUBSCRIBE', {
                            'id': f'{conn_id}-{ticker}-tk',
                            'destination': 'MXSE.orderbooks',
                            'selector': f"TICKER='MXSE.TQBR.{ticker}'"
                        })
                        await asyncio.sleep(0.01)

                    if SUB_SELECTOR_MODE in ('SECID', 'AUTO'):
                        await send_frame(ws, 'SUBSCRIBE', {
                            'id': f'{conn_id}-{ticker}-sc',
                            'destination': 'MXSE.orderbooks',
                            'selector': f"SECID='{ticker}'"
                        })
                        await asyncio.sleep(0.01)
                
                monitor.set_conn_status(conn_id, 'online')
                reconnect_delay = 5
                
                # Message loop
                while not stop.is_set():
                    try:
                        frame = await asyncio.wait_for(recv_frame(ws), timeout=60.0)
                        
                        if frame.cmd == 'MESSAGE':
                            raw_body = frame.body.strip('\0') if isinstance(frame.body, str) else frame.body.decode('utf8').strip('\0')
                            if DEBUG_FRAMES and monitor._debug_msg_count_by_conn[conn_id] < 3:
                                monitor._debug_msg_count_by_conn[conn_id] += 1
                                print(f"\n{C.Y}[DEBUG][conn {conn_id}] MESSAGE headers={frame.headers} body_sample={raw_body[:120]}...{C.END}")

                            body = json.loads(raw_body)
                            ticker_full = body.get('TICKER', '')
                            ticker = ticker_full.split('.')[-1] if ticker_full else None
                            
                            # Альтернативное поле тикера
                            if not ticker:
                                ticker = body.get('SECID')
                            
                            if ticker:
                                await monitor.update_ticker(conn_id, ticker, body)
                        
                        elif frame.cmd == 'ERROR':
                            if DEBUG_FRAMES:
                                print(f"{C.R}[DEBUG][conn {conn_id}] ERROR headers={frame.headers}{C.END}")
                            monitor.set_conn_status(conn_id, 'error')
                            break
                    
                    except asyncio.TimeoutError:
                        pass
        
        except ConnectionClosed:
            monitor.set_conn_status(conn_id, 'closed')
        except Exception as e:
            monitor.set_conn_status(conn_id, f'err:{str(e)[:10]}')
        
        if not stop.is_set():
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 1.5, 60)


async def main():
    # Начальное сообщение
    print(f"{C.C}Initializing MOEX Monitor...{C.END}\n")
    
    NUM_CONNECTIONS = 30
    TICKERS_PER_CONNECTION = 50
    
    # Получаем все тикеры
    print(f"{C.B}→ Loading tickers from MOEX ISS API...{C.END}")
    url = "https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json"
    
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.loads(r.read())
    
    cols = data['securities']['columns']
    all_tickers = [row[cols.index('SECID')] for row in data['securities']['data'] if row[cols.index('SECID')]]
    
    print(f"{C.G}✓ Loaded {len(all_tickers)} tickers{C.END}")
    
    # Генерируем группы
    print(f"{C.B}→ Generating {NUM_CONNECTIONS} random groups...{C.END}")
    ticker_groups = []
    
    for i in range(NUM_CONNECTIONS):
        group = random.sample(all_tickers, min(TICKERS_PER_CONNECTION, len(all_tickers)))
        ticker_groups.append(group)
    
    total_subscriptions = sum(len(g) for g in ticker_groups)
    print(f"{C.G}✓ Total subscriptions: {total_subscriptions}{C.END}\n")
    
    monitor = GlobalMonitor()
    stop = asyncio.Event()
    
    def handler(sig, frame):
        stop.set()
    
    signal.signal(signal.SIGINT, handler)
    
    print(f"{C.B}→ Starting {NUM_CONNECTIONS} WebSocket clients...{C.END}")
    print(f"{C.Y}(Starting display in 5 seconds...){C.END}\n")
    
    # Запускаем клиенты
    clients = []
    for i in range(NUM_CONNECTIONS):
        task = asyncio.create_task(
            websocket_client(i+1, ticker_groups[i], monitor, stop)
        )
        clients.append(task)
        await asyncio.sleep(0.15)  # Задержка между запусками
    
    # Ждем немного перед началом display
    await asyncio.sleep(5)
    
    # Запускаем дисплей
    display_task = asyncio.create_task(display_loop(monitor, stop))
    
    # Ждем завершения
    await asyncio.gather(*clients, display_task, return_exceptions=True)
    
    # Очистка и финальная статистика
    print(f"{C.CLEAR}{C.HOME}")
    print(f"\n{C.G}{'='*80}")
    print(f"  FINAL STATISTICS")
    print(f"{'='*80}{C.END}")
    
    s = monitor.get_summary()
    print(f"Runtime: {s['uptime']}s")
    print(f"Total Updates: {C.C}{s['total_messages']}{C.END}")
    print(f"Unique Tickers: {C.M}{s['unique_tickers']}{C.END}")
    print(f"With Prices: {C.G}{s['with_prices']}{C.END}")
    print(f"Average Rate: {C.Y}{s['rate']:.2f} msg/s{C.END}")
    print(f"Connections: {s['connections_active']}/{s['connections_total']}")
    print(f"\n{C.G}✓ Done{C.END}\n")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{C.Y}Stopped{C.END}\n")

