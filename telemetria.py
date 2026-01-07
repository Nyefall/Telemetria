"""
Sistema de Telemetria de Hardware - Launcher Unificado
Permite ao usuário selecionar entre Sender ou Receiver
"""
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import ctypes

# Detectar se está rodando como executável empacotado
def get_base_path():
    """Retorna o caminho base (para PyInstaller ou desenvolvimento)"""
    if getattr(sys, 'frozen', False):
        # Rodando como executável empacotado
        return sys._MEIPASS
    else:
        # Rodando como script Python
        return os.path.dirname(os.path.abspath(__file__))

def is_admin():
    """Verifica se está rodando como administrador"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """Reinicia o executável com privilégios de administrador"""
    if sys.platform == 'win32':
        if getattr(sys, 'frozen', False):
            # Executável empacotado
            exe_path = sys.executable
        else:
            # Script Python
            exe_path = sys.executable
            
        params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
        
        # Adicionar flag para ir direto ao sender
        params = f'"--sender" {params}' if params else '"--sender"'
        
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", exe_path,
            params, None, 1
        )
        sys.exit(0)

# Adicionar o caminho base ao sys.path para imports
BASE_PATH = get_base_path()
if BASE_PATH not in sys.path:
    sys.path.insert(0, BASE_PATH)

class TelemetriaLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sistema de Telemetria")
        self.root.geometry("520x520")
        self.root.resizable(False, False)
        self.root.configure(bg='#2b2b2b')
        
        # Configurar UI primeiro
        self.setup_ui()
        
        # Centralizar janela depois de configurar UI
        self.center_window()
        
    def center_window(self):
        """Centraliza a janela na tela"""
        self.root.update_idletasks()
        width = 520
        height = 520
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def setup_ui(self):
        """Configura a interface do launcher"""
        # Frame principal
        main_frame = tk.Frame(self.root, bg='#2b2b2b')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Título
        title_label = tk.Label(
            main_frame,
            text="📡 Sistema de Telemetria",
            font=('Segoe UI', 24, 'bold'),
            fg='#ffffff',
            bg='#2b2b2b'
        )
        title_label.pack(pady=(20, 10))
        
        subtitle_label = tk.Label(
            main_frame,
            text="Monitoramento de Hardware em Tempo Real",
            font=('Segoe UI', 11),
            fg='#888888',
            bg='#2b2b2b'
        )
        subtitle_label.pack(pady=(0, 40))
        
        # Frame de seleção
        selection_frame = tk.Frame(main_frame, bg='#2b2b2b')
        selection_frame.pack(pady=20)
        
        label = tk.Label(
            selection_frame,
            text="Selecione o modo de operação:",
            font=('Segoe UI', 12),
            fg='#ffffff',
            bg='#2b2b2b'
        )
        label.pack(pady=(0, 20))
        
        # Botão Sender
        sender_frame = tk.Frame(selection_frame, bg='#3a3a3a', relief=tk.RAISED, bd=2)
        sender_frame.pack(pady=10, fill=tk.X)
        
        sender_btn = tk.Button(
            sender_frame,
            text="💻 SENDER (PC Principal)",
            font=('Segoe UI', 14, 'bold'),
            bg='#0d7377',
            fg='#ffffff',
            activebackground='#14A085',
            activeforeground='#ffffff',
            cursor='hand2',
            relief=tk.FLAT,
            padx=30,
            pady=15,
            command=self.launch_sender
        )
        sender_btn.pack(fill=tk.X)
        
        sender_desc = tk.Label(
            sender_frame,
            text="Coleta e envia dados dos sensores de hardware\n(Requer privilégios de Administrador)",
            font=('Segoe UI', 9),
            fg='#aaaaaa',
            bg='#3a3a3a',
            justify=tk.LEFT
        )
        sender_desc.pack(pady=(5, 10), padx=10)
        
        # Botão Receiver
        receiver_frame = tk.Frame(selection_frame, bg='#3a3a3a', relief=tk.RAISED, bd=2)
        receiver_frame.pack(pady=10, fill=tk.X)
        
        receiver_btn = tk.Button(
            receiver_frame,
            text="📊 RECEIVER (Dashboard)",
            font=('Segoe UI', 14, 'bold'),
            bg='#323e8a',
            fg='#ffffff',
            activebackground='#4150b5',
            activeforeground='#ffffff',
            cursor='hand2',
            relief=tk.FLAT,
            padx=30,
            pady=15,
            command=self.launch_receiver
        )
        receiver_btn.pack(fill=tk.X)
        
        receiver_desc = tk.Label(
            receiver_frame,
            text="Exibe dashboard com telemetria em tempo real\n(Pode rodar em qualquer dispositivo da rede)",
            font=('Segoe UI', 9),
            fg='#aaaaaa',
            bg='#3a3a3a',
            justify=tk.LEFT
        )
        receiver_desc.pack(pady=(5, 10), padx=10)
        
        # Rodapé
        footer = tk.Label(
            main_frame,
            text="v1.0 | Desenvolvido por @Nyefall",
            font=('Segoe UI', 9),
            fg='#666666',
            bg='#2b2b2b'
        )
        footer.pack(side=tk.BOTTOM, pady=(30, 0))
        
    def launch_sender(self):
        """Inicia o modo Sender"""
        # Verificar se tem privilégios de admin
        if not is_admin():
            result = messagebox.askyesno(
                "Privilégios de Administrador",
                "O Sender requer privilégios de Administrador para acessar sensores de hardware.\n\n"
                "Deseja reiniciar como Administrador?",
                icon='warning'
            )
            if result:
                self.root.destroy()
                run_as_admin()
            return
        
        self.root.destroy()
        try:
            # Desativar auto-elevação do sender já que já somos admin
            sys.argv.append('--no-admin')
            import sender_pc
            sender_pc.main()
        except ImportError as e:
            messagebox.showerror("Erro", f"Erro ao importar sender_pc: {e}\nBASE_PATH: {BASE_PATH}")
            sys.exit(1)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao iniciar Sender: {e}")
            sys.exit(1)
            
    def launch_receiver(self):
        """Inicia o modo Receiver"""
        self.root.destroy()
        try:
            import receiver_notebook
            receiver_notebook.main()
        except ImportError as e:
            messagebox.showerror("Erro", f"Erro ao importar receiver_notebook: {e}\nBASE_PATH: {BASE_PATH}")
            sys.exit(1)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao iniciar Receiver: {e}")
            sys.exit(1)
            
    def run(self):
        """Executa o launcher"""
        self.root.mainloop()

def main():
    """Função principal"""
    # Verificar se foi chamado com --sender (após elevação de privilégios)
    if '--sender' in sys.argv:
        sys.argv.append('--no-admin')  # Evitar loop de elevação
        try:
            import sender_pc
            sender_pc.main()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao iniciar Sender: {e}")
            sys.exit(1)
        return
    
    # Verificar se foi chamado com --receiver
    if '--receiver' in sys.argv:
        try:
            import receiver_notebook
            receiver_notebook.main()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao iniciar Receiver: {e}")
            sys.exit(1)
        return
    
    # Mostrar launcher normalmente
    launcher = TelemetriaLauncher()
    launcher.run()

if __name__ == "__main__":
    main()
