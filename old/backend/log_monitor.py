#!/usr/bin/env python3
"""
Monitor avançado de logs para desenvolvimento do CostsHub
Monitora logs em tempo real com filtros e cores
"""

import time
import os
import sys
from datetime import datetime
import re
from collections import deque

class LogMonitor:
    def __init__(self, log_file='backend.log'):
        self.log_file = log_file
        self.last_position = 0
        self.buffer = deque(maxlen=1000)  # Buffer para últimas 1000 linhas
        
        # Cores ANSI
        self.colors = {
            'RED': '\033[0;31m',
            'GREEN': '\033[0;32m',
            'YELLOW': '\033[1;33m',
            'BLUE': '\033[0;34m',
            'PURPLE': '\033[0;35m',
            'CYAN': '\033[0;36m',
            'WHITE': '\033[1;37m',
            'RESET': '\033[0m'
        }
        
        # Padrões para destacar
        self.patterns = {
            'ERROR': (self.colors['RED'], ['ERROR', '❌', 'Exception', 'Traceback']),
            'WARNING': (self.colors['YELLOW'], ['WARNING', '⚠️', 'WARN']),
            'EMAIL': (self.colors['PURPLE'], ['📧', 'email', 'Email', 'SMTP', 'SES']),
            'INVITE': (self.colors['BLUE'], ['🔄', 'convite', 'invite', 'invitation']),
            'SUCCESS': (self.colors['GREEN'], ['✅', 'SUCCESS', 'enviado com sucesso']),
            'DEBUG': (self.colors['CYAN'], ['🔍', 'DEBUG', 'Tentando']),
            'API': (self.colors['WHITE'], ['POST', 'GET', 'PUT', 'DELETE', 'OPTIONS'])
        }
    
    def colorize_line(self, line):
        """Aplica cores baseado no conteúdo da linha"""
        for category, (color, keywords) in self.patterns.items():
            for keyword in keywords:
                if keyword.lower() in line.lower():
                    return f"{color}{line}{self.colors['RESET']}"
        return line
    
    def format_timestamp(self):
        """Retorna timestamp formatado"""
        return datetime.now().strftime("%H:%M:%S")
    
    def print_header(self):
        """Imprime cabeçalho do monitor"""
        print(f"{self.colors['CYAN']}{'='*80}{self.colors['RESET']}")
        print(f"{self.colors['WHITE']}🔍 MONITOR DE LOGS CONTÍNUO - CostsHub{self.colors['RESET']}")
        print(f"{self.colors['CYAN']}{'='*80}{self.colors['RESET']}")
        print(f"{self.colors['YELLOW']}📋 Arquivo: {self.log_file}{self.colors['RESET']}")
        print(f"{self.colors['YELLOW']}🎯 Monitorando: Emails, Convites, Erros, APIs{self.colors['RESET']}")
        print(f"{self.colors['YELLOW']}⌨️  Comandos: Ctrl+C (sair), 'f' (filtrar), 'c' (limpar){self.colors['RESET']}")
        print(f"{self.colors['CYAN']}{'='*80}{self.colors['RESET']}")
        print()
    
    def show_recent_logs(self, lines=10):
        """Mostra as últimas N linhas do log"""
        if not os.path.exists(self.log_file):
            print(f"{self.colors['RED']}❌ Arquivo de log não encontrado: {self.log_file}{self.colors['RESET']}")
            return
        
        print(f"{self.colors['CYAN']}📜 ÚLTIMAS {lines} LINHAS:{self.colors['RESET']}")
        print("-" * 50)
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) >= lines else all_lines
                
                for line in recent_lines:
                    line = line.strip()
                    if line:
                        colored_line = self.colorize_line(line)
                        print(f"[{self.format_timestamp()}] {colored_line}")
                
                # Atualizar posição para monitoramento contínuo
                self.last_position = f.tell() if hasattr(f, 'tell') else len(''.join(all_lines))
                
        except Exception as e:
            print(f"{self.colors['RED']}❌ Erro ao ler arquivo: {str(e)}{self.colors['RESET']}")
        
        print()
        print(f"{self.colors['GREEN']}🔄 INICIANDO MONITORAMENTO EM TEMPO REAL...{self.colors['RESET']}")
        print("-" * 50)
    
    def monitor_continuous(self):
        """Monitora logs continuamente"""
        if not os.path.exists(self.log_file):
            print(f"{self.colors['RED']}❌ Arquivo de log não encontrado: {self.log_file}{self.colors['RESET']}")
            return
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                # Ir para o final do arquivo
                f.seek(0, 2)  # Seek to end
                
                while True:
                    line = f.readline()
                    if line:
                        line = line.strip()
                        if line:
                            colored_line = self.colorize_line(line)
                            timestamp = self.format_timestamp()
                            print(f"[{timestamp}] {colored_line}")
                            
                            # Adicionar ao buffer
                            self.buffer.append((timestamp, line))
                    else:
                        time.sleep(0.1)  # Aguardar novas linhas
                        
        except KeyboardInterrupt:
            print(f"\n{self.colors['YELLOW']}🛑 Monitoramento interrompido pelo usuário{self.colors['RESET']}")
        except Exception as e:
            print(f"{self.colors['RED']}❌ Erro no monitoramento: {str(e)}{self.colors['RESET']}")
    
    def run(self):
        """Executa o monitor"""
        self.print_header()
        self.show_recent_logs(10)
        self.monitor_continuous()

def main():
    """Função principal"""
    log_file = 'backend.log'
    
    # Verificar se arquivo existe
    if not os.path.exists(log_file):
        print("❌ Arquivo backend.log não encontrado!")
        print("💡 Certifique-se de que o backend está rodando")
        print("💡 Execute: python -m flask run --port 5001 --debug")
        sys.exit(1)
    
    # Iniciar monitor
    monitor = LogMonitor(log_file)
    monitor.run()

if __name__ == "__main__":
    main()
