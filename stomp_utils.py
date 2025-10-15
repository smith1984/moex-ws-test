"""
Упрощенная реализация STOMP протокола для MOEX WebSocket API
"""

class Frame:
    """STOMP Frame"""
    def __init__(self, cmd, headers=None, body=''):
        self.cmd = cmd
        self.headers = headers or {}
        self.body = body


def convert_frame(frame):
    """Конвертирует Frame в байты для отправки"""
    lines = [frame.cmd.encode('utf-8')]
    
    for key, value in frame.headers.items():
        lines.append(f'{key}:{value}'.encode('utf-8'))
    
    lines.append(b'')
    
    if isinstance(frame.body, str):
        lines.append(frame.body.encode('utf-8'))
    elif isinstance(frame.body, bytes):
        lines.append(frame.body)
    
    lines.append(b'\x00')
    
    return [b'\n'.join(lines)]


def parse_frame(data):
    """Парсит STOMP frame из байтов"""
    if isinstance(data, bytes):
        data = data.decode('utf-8')
    
    # Удаляем null-терминатор
    data = data.rstrip('\x00')
    
    lines = data.split('\n')
    
    if not lines:
        return Frame('ERROR', {}, '')
    
    cmd = lines[0]
    headers = {}
    body_start = 1
    
    for i, line in enumerate(lines[1:], 1):
        if line == '':
            body_start = i + 1
            break
        
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key] = value
    
    body = '\n'.join(lines[body_start:]) if body_start < len(lines) else ''
    
    return Frame(cmd, headers, body)
