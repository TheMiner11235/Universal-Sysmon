import psutil, platform, subprocess, time, os
from dataclasses import dataclass
from typing import List, Dict

try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
except:
    class Fore: BLACK = RED = GREEN = YELLOW = BLUE = CYAN = WHITE = RESET = ''
    class Style: BRIGHT = RESET_ALL = DIM = ''
    class Back: BLACK = RESET = ''

IS_WINDOWS = platform.system() == 'Windows'
IS_LINUX = platform.system() == 'Linux'
IS_MAC = platform.system() == 'Darwin'

@dataclass
class Theme:
    bg: str; bar: str; empty: str; text: str; dim: str; bright: str; border: str
    low: str; med: str; high: str; crit: str

DARK = Theme(Back.BLACK, Fore.WHITE, Style.DIM, Fore.WHITE, Style.DIM, Style.BRIGHT, Fore.WHITE, Fore.CYAN, Fore.GREEN, Fore.YELLOW, Fore.RED)
LIGHT = Theme('', Fore.BLACK, Style.DIM+Fore.BLACK, Fore.BLACK, Style.DIM+Fore.BLACK, Style.BRIGHT+Fore.BLACK, Fore.BLACK, Fore.GREEN, Fore.YELLOW, Fore.RED, Fore.RED+Style.BRIGHT)
RESET = Style.RESET_ALL

def _c(usage: float, t: Theme) -> str:
    if usage <= 40: return t.low
    elif usage <= 70: return t.med
    elif usage <= 90: return t.high
    return t.crit

def _bar(usage: float, w: int, t: Theme) -> str:
    f = int((usage / 100) * w)
    e = w - f
    c = _c(usage, t)
    return f"[{c}{'|'*f}{t.empty}{'-'*e}{RESET}] {t.text}{usage:5.1f}%{RESET}"

def _run(cmd: List[str]) -> str:
    try: return subprocess.run(cmd, capture_output=True, text=True, timeout=2).stdout
    except: return ''

def _run_piped(cmd: str) -> str:
    try: return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=2).stdout
    except: return ''

class SystemMonitor:
    def __init__(self, refresh=0.1, width=50, theme=DARK, show_all=True):
        self.r, self.w, self.t, self.all = refresh, width, theme, show_all
    
    def _cpu(self) -> Dict:
        name = "CPU"
        if IS_WINDOWS:
            try:
                out = _run(['wmic', 'cpu', 'get', 'Name', '/format:value'])
                for line in out.split('\n'):
                    if 'Name=' in line:
                        name = line.split('=', 1)[1].strip()
                        break
            except: pass
        elif IS_LINUX:
            out = _run_piped("cat /proc/cpuinfo | grep 'model name' | head -1")
            if 'model name' in out:
                name = out.split(':')[1].strip()
        elif IS_MAC:
            out = _run_piped("sysctl -n machdep.cpu.brand_string")
            if out.strip():
                name = out.strip()
        
        freq = psutil.cpu_freq()
        return {'name': name or 'CPU', 'usage': psutil.cpu_percent(interval=0.1),
                'freq': (freq.current/1000, freq.max/1000) if freq else (0,0)}
    
    def _gpu(self) -> List[Dict]:
        gpus = []
        
        if IS_WINDOWS:
            out = _run(['wmic', 'path', 'Win32_VideoController', 'get', 'Name,AdapterRAM', '/format:list'])
            for line in out.split('\n'):
                if line.startswith('Name='):
                    name = line.split('=', 1)[1].strip()
                    if 'AMD' in name or 'Radeon' in name or 'Intel' in name or 'NVIDIA' in name:
                        vendor = 'NVIDIA' if 'NVIDIA' in name else ('AMD' if ('AMD' in name or 'Radeon' in name) else 'Intel')
                        gpus.append({'name': name, 'vendor': vendor, 'usage': 0, 'vram_used': 0, 'vram_total': 8<<30, 'freq': 0, 'vram_freq': 0, 'temp': 0, 'power': 0, 'fan': 0})
                        break
            if not gpus:
                try:
                    import pynvml
                    pynvml.nvmlInit()
                    for i in range(pynvml.nvmlDeviceGetCount()):
                        h = pynvml.nvmlDeviceGetHandleByIndex(i)
                        m = pynvml.nvmlDeviceGetMemoryInfo(h)
                        gpus.append({'name': pynvml.nvmlDeviceGetName(h), 'vendor': 'NVIDIA',
                                     'usage': pynvml.nvmlDeviceGetUtilizationRates(h).gpu,
                                     'vram_used': m.used, 'vram_total': m.total,
                                     'freq': pynvml.nvmlDeviceGetClockInfo(h, 0)/1000,
                                     'vram_freq': 0, 'temp': 0, 'power': 0, 'fan': 0})
                except: pass
        
        elif IS_LINUX:
            # Try NVIDIA
            try:
                import pynvml
                pynvml.nvmlInit()
                for i in range(pynvml.nvmlDeviceGetCount()):
                    h = pynvml.nvmlDeviceGetHandleByIndex(i)
                    m = pynvml.nvmlDeviceGetMemoryInfo(h)
                    gpus.append({'name': pynvml.nvmlDeviceGetName(h), 'vendor': 'NVIDIA',
                                 'usage': pynvml.nvmlDeviceGetUtilizationRates(h).gpu,
                                 'vram_used': m.used, 'vram_total': m.total,
                                 'freq': pynvml.nvmlDeviceGetClockInfo(h, 0)/1000,
                                 'vram_freq': 0, 'temp': 0, 'power': 0, 'fan': 0})
            except: pass
            
            # Try AMD via amdsmi
            if not gpus:
                try:
                    import amdsmi
                    devices = amdsmi.amdsmi_get_processor_handles()
                    for i, device in enumerate(devices):
                        info = amdsmi.amdsmi_get_gpu_device_info(device)
                        gpus.append({
                            'index': i, 'vendor': 'AMD', 'name': info.get('name', 'AMD GPU'),
                            'usage': 0, 'vram_used': 0, 'vram_total': info.get('vram_memory_size', 8<<30),
                            'freq': 0, 'vram_freq': 0, 'temp': 0, 'power': 0, 'fan': 0
                        })
                except: pass
        
        elif IS_MAC:
            out = _run_piped("system_profiler SPDisplaysDataType | grep -E 'Chipset|Model'")
            if 'AMD' in out or 'Intel' in out or 'Apple' in out:
                vendor = 'Apple' if 'Apple' in out else ('AMD' if 'AMD' in out else 'Intel')
                name = out.strip().split('\n')[0] if '\n' in out else out.strip()
                gpus.append({'name': name, 'vendor': vendor, 'usage': 0, 'vram_used': 0, 'vram_total': 8<<30, 'freq': 0, 'vram_freq': 0, 'temp': 0, 'power': 0, 'fan': 0})
        
        return gpus
    
    def _gpu_update(self, g: Dict):
        if g.get('vendor') != 'AMD' or not IS_WINDOWS:
            return
        try:
            code = 'import ADLXPybind as adlx; h=adlx.ADLXHelper(); h.InitializeWithIncompatibleDriver(); ss=h.GetSystemServices(); pms=ss.GetPerformanceMonitoringServices(); [print(f"{pms.GetCurrentGPUMetrics(x).GPUUsage()},{pms.GetCurrentGPUMetrics(x).GPUVRAM()},{pms.GetCurrentGPUMetrics(x).GPUVRAMClockSpeed()}") for x in list(ss.GetGPUsEx()) if pms.GetCurrentGPUMetrics(x)]'
            result = subprocess.run(['python', '-c', code], capture_output=True, text=True, timeout=3)
            if result.stdout.strip():
                parts = result.stdout.strip().split(',')
                if len(parts) >= 3:
                    g['usage'] = float(parts[0])
                    g['vram_used'] = float(parts[1]) * 1024**2
                    g['vram_freq'] = float(parts[2])
        except: pass
    
    def _gpu_update_linux(self, g: Dict):
        if g.get('vendor') != 'AMD' or not IS_LINUX:
            return
        try:
            import amdsmi
            for device in amdsmi.amdsmi_get_processor_handles():
                metrics = amdsmi.amdsmi_get_gpu_metrics(device)
                g['usage'] = metrics.get('current_gpu_busy_percent', 0)
                g['vram_used'] = metrics.get('vram_usage', 0)
                g['freq'] = metrics.get('current_sclk_mhz', 0) / 1000
                g['temp'] = metrics.get('temperature_edge', 0)
                g['power'] = metrics.get('current_socket_power', 0) / 1000
                break
        except: pass
    
    def _ram(self) -> Dict:
        m = psutil.virtual_memory()
        return {'total': m.total, 'used': m.used, 'usage': m.percent}
    
    def _disk(self) -> List[Dict]:
        disks = []
        
        if IS_WINDOWS:
            boot = _run(['wmic', 'os', 'get', 'SystemDrive']).split('=')[-1].strip()
        else:
            boot = '/'
        
        prev = {p.device: psutil.disk_io_counters()._asdict() for p in psutil.disk_partitions()}
        time.sleep(0.1)
        curr = {p.device: psutil.disk_io_counters()._asdict() for p in psutil.disk_partitions()}
        
        for p in psutil.disk_partitions():
            if 'cdrom' in p.opts.lower() or 'removable' in p.opts.lower():
                continue
            try:
                u = psutil.disk_usage(p.mountpoint)
                disks.append({'device': p.device, 'mount': p.mountpoint, 'total': u.total, 'used': u.used, 'usage': (u.used/u.total)*100,
                              'boot': p.device.startswith(boot.replace('\\','')) if IS_WINDOWS else p.mountpoint == '/',
                              'type': 'SSD', 'read': 0, 'write': 0})
            except: continue
        
        for d in disks:
            if d['device'] in curr and d['device'] in prev:
                d['read'] = (curr[d['device']]['read_bytes']-prev[d['device']]['read_bytes'])/0.1
                d['write'] = (curr[d['device']]['write_bytes']-prev[d['device']]['write_bytes'])/0.1
        
        return disks
    
    def _net(self) -> Dict:
        prev = psutil.net_io_counters(pernic=True)
        time.sleep(0.1)
        curr = psutil.net_io_counters(pernic=True)
        stats = psutil.net_if_stats()
        for nic, d in curr.items():
            if d.bytes_recv > 0 and (stats.get(nic) or {}).isup:
                return {'name': nic, 'recv': d.bytes_recv-prev[nic].bytes_recv, 'sent': d.bytes_sent-prev[nic].bytes_sent}
        return {'name': 'None', 'recv': 0, 'sent': 0}
    
    def _fmt_size(self, b: float) -> str:
        g = b / 1024**3
        return f"{g:.1f} GB" if g >= 1 else f"{g*1024:.0f} MB"
    
    def _fmt_speed(self, b: float) -> str:
        for u in ['', 'K', 'M', 'G']:
            if abs(b) < 1024: return f"{b:.1f} {u}B/s"
            b /= 1024
        return f"{b:.1f} TB/s"
    
    def run(self):
        print('\033[2J\033[H', end='')
        try:
            while True:
                try:
                    w = min(80, os.get_terminal_size().columns)
                except:
                    w = 80
                print('\033[2J\033[H', end='')
                
                cpu = self._cpu()
                gpu_list = self._gpu()
                for g in gpu_list:
                    if g['vendor'] == 'AMD':
                        if IS_WINDOWS:
                            self._gpu_update(g)
                        elif IS_LINUX:
                            self._gpu_update_linux(g)
                
                lines = [
                    f"+{'='*(w-2)}+",
                    f"|{'SYSTEM RESOURCE MONITOR'.center(w-2)}|",
                    f"|{platform.system().center(w-2)}|",
                    f"+{'-'*(w-2)}+",
                    "",
                    f"  CPU: {cpu['name']}",
                    f"  {_bar(cpu['usage'], self.w, self.t)} | {cpu['freq'][0]:.2f} GHz"
                ]
                
                for g in gpu_list:
                    lines += [
                        f"  GPU: {g['name']}",
                        f"  {_bar(g['usage'], self.w, self.t)} | VRAM: {self._fmt_size(g['vram_used'])}/{self._fmt_size(g['vram_total'])}",
                        ""]
                
                r = self._ram()
                lines += [
                    f"  RAM:",
                    f"  {_bar(r['usage'], self.w, self.t)} | {self._fmt_size(r['used'])}/{self._fmt_size(r['total'])}",
                    ""]
                
                for d in self._disk():
                    label = "Disk" if d['mount'] == '/' else d['device']
                    boot = " [BOOT]" if d['boot'] else ""
                    lines += [
                        f"  {label}{boot}",
                        f"  {_bar(d['usage'], self.w, self.t)} | {self._fmt_size(d['used'])}/{self._fmt_size(d['total'])}",
                        f"  I/O: R:{self._fmt_speed(d['read'])} W:{self._fmt_speed(d['write'])}",
                        ""]
                
                n = self._net()
                lines += [
                    f"  Net: {n['name']}",
                    f"  DL: {self._fmt_speed(n['recv'])} | UL: {self._fmt_speed(n['sent'])}",
                    f"+{'='*(w-2)}+",
                    f"|{f'Refresh: {self.r}s | Ctrl+C to exit'.center(w-2)}|",
                    f"+{'='*(w-2)}+"
                ]
                
                for l in lines: print(f"\r{l}")
                time.sleep(self.r)
        except KeyboardInterrupt:
            print("\r\nExiting...")

def main():
    import argparse
    p = argparse.ArgumentParser(description='System Resource Monitor')
    p.add_argument('-r', '--refresh', type=float, default=0.1, help='Refresh rate in seconds')
    p.add_argument('-w', '--width', type=int, default=50, help='Progress bar width')
    p.add_argument('--theme', choices=['dark','light'], default='dark', help='Color theme')
    args = p.parse_args()
    SystemMonitor(args.refresh, args.width, DARK if args.theme=='dark' else LIGHT).run()

if __name__ == '__main__':
    main()