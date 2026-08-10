import os
import json
from datetime import datetime
from typing import Dict, Optional
import hashlib

class CacheManager:
    """
    Gestor de caché centralizado para evitar saturar APIs externas.
    Implementa invalidación automática por fecha.
    """
    
    def __init__(self, cache_dir: str = '.cache'):
        self.cache_dir = cache_dir
        self.fecha_hoy = datetime.today().strftime('%Y-%m-%d')
        
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    
    def _generar_clave(self, *args) -> str:
        """
        Genera una clave hash única para una consulta.
        
        Args:
            *args: Componentes de la clave
            
        Returns:
            Hash MD5 de la clave
        """
        clave_str = "_".join(str(arg) for arg in args) + f"_{self.fecha_hoy}"
        return hashlib.md5(clave_str.encode()).hexdigest()
    
    def _obtener_ruta(self, categoria: str, clave: str) -> str:
        """
        Obtiene la ruta del archivo de caché.
        
        Args:
            categoria: Tipo de dato (bateo, bullpen, pitcher, etc)
            clave: Hash de la consulta
            
        Returns:
            Ruta del archivo
        """
        categoria_dir = os.path.join(self.cache_dir, categoria)
        if not os.path.exists(categoria_dir):
            os.makedirs(categoria_dir)
        return os.path.join(categoria_dir, f"{clave}.json")
    
    def obtener(self, categoria: str, *args) -> Optional[Dict]:
        """
        Obtiene datos del caché si existen.
        
        Args:
            categoria: Tipo de dato
            *args: Parámetros de búsqueda
            
        Returns:
            Diccionario con datos o None
        """
        clave = self._generar_clave(*args)
        ruta = self._obtener_ruta(categoria, clave)
        
        if os.path.exists(ruta):
            try:
                with open(ruta, 'r') as f:
                    datos = json.load(f)
                    print(f"✅ Caché hit: {categoria}")
                    return datos
            except Exception as e:
                print(f"⚠️ Error leyendo caché: {e}")
                return None
        
        return None
    
    def guardar(self, categoria: str, datos: Dict, *args) -> None:
        """
        Guarda datos en el caché.
        
        Args:
            categoria: Tipo de dato
            datos: Diccionario a guardar
            *args: Parámetros de búsqueda
        """
        clave = self._generar_clave(*args)
        ruta = self._obtener_ruta(categoria, clave)
        
        try:
            with open(ruta, 'w') as f:
                json.dump(datos, f, indent=2)
                print(f"💾 Caché guardado: {categoria}")
        except Exception as e:
            print(f"⚠️ Error guardando caché: {e}")
    
    def limpiar_categoria(self, categoria: str) -> None:
        """
        Limpia todos los archivos de una categoría.
        
        Args:
            categoria: Tipo de dato a limpiar
        """
        categoria_dir = os.path.join(self.cache_dir, categoria)
        if os.path.exists(categoria_dir):
            for archivo in os.listdir(categoria_dir):
                os.remove(os.path.join(categoria_dir, archivo))
            print(f"🗑️ Caché limpiado: {categoria}")
