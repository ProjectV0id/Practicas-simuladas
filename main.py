
# IMPORTACIONES NECESARIAS
import tkinter as tk                          # Librería GUI principal de Python
from tkinter import ttk, messagebox, scrolledtext  # Widgets adicionales de Tkinter
import datetime                               # Para manejar fechas y horas
import os                                     # Para operaciones del sistema de archivos
import re                                     # Para expresiones regulares (validación)
from abc import ABC, abstractmethod           # Para clases abstractas


# Creé mensajes de error personalizados para controlar mejor los problemas del sistema.

class SoftwareFJError(Exception):
    """
    Excepción base del sistema Software FJ.
    Todas las excepciones personalizadas heredan de esta clase.
    Esto nos permite capturar cualquier error del sistema con un solo except.
    """
    def __init__(self, mensaje, codigo=None):
        # Llamamos al constructor de la clase padre (Exception)
        super().__init__(mensaje)
        self.mensaje = mensaje          # Guardamos el mensaje de error
        self.codigo = codigo            # Código opcional para identificar el tipo de error
        # Registramos la hora exacta en que ocurrió el error
        self.timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def __str__(self):
        # Definimos cómo se muestra la excepción como texto
        if self.codigo:
            return f"[{self.codigo}] {self.mensaje}"
        return self.mensaje


class ClienteInvalidoError(SoftwareFJError):
    """
    Se lanza cuando los datos de un cliente no son válidos.
    Ejemplo: nombre vacío, email con formato incorrecto, teléfono inválido.
    """
    def __init__(self, campo, valor, detalle=""):
        # Construimos un mensaje descriptivo con el campo y valor problemático
        mensaje = f"Dato inválido en campo '{campo}': '{valor}'. {detalle}"
        super().__init__(mensaje, codigo="ERR_CLIENTE")
        self.campo = campo       # Qué campo tiene el error
        self.valor = valor       # Qué valor inválido se intentó asignar


class ServicioInvalidoError(SoftwareFJError):
    """
    Se lanza cuando la configuración de un servicio es incorrecta.
    Ejemplo: precio negativo, capacidad cero, duración inválida.
    """
    def __init__(self, servicio, problema):
        mensaje = f"Servicio inválido '{servicio}': {problema}"
        super().__init__(mensaje, codigo="ERR_SERVICIO")


class ReservaError(SoftwareFJError):
    """
    Se lanza cuando una reserva no puede completarse.
    Ejemplo: servicio no disponible, cliente no registrado.
    """
    def __init__(self, motivo, reserva_id=None):
        # Si tenemos ID de reserva, lo incluimos en el mensaje
        prefijo = f"Reserva #{reserva_id} - " if reserva_id else ""
        mensaje = f"{prefijo}Error en reserva: {motivo}"
        super().__init__(mensaje, codigo="ERR_RESERVA")


class DisponibilidadError(SoftwareFJError):
    """
    Se lanza cuando un servicio no tiene disponibilidad.
    Ejemplo: sala ya reservada, equipo agotado.
    """
    def __init__(self, servicio, fecha=None):
        fecha_str = f" para el {fecha}" if fecha else ""
        mensaje = f"Servicio '{servicio}' no disponible{fecha_str}"
        super().__init__(mensaje, codigo="ERR_DISPONIBILIDAD")


class CalculoError(SoftwareFJError):
    """
    Se lanza cuando hay inconsistencias en cálculos de costos.
    Ejemplo: descuento mayor al 100%, parámetros incoherentes.
    """
    def __init__(self, descripcion):
        mensaje = f"Error en cálculo: {descripcion}"
        super().__init__(mensaje, codigo="ERR_CALCULO")

# Implementé un sistema de registros para guardar las acciones y eventos importantes del sistema.

class SistemaLogs:
    """
    Clase para registrar todos los eventos y errores del sistema.
    Usa el patrón Singleton: solo existe UNA instancia de esta clase.
    Guarda los logs en un archivo de texto plano.
    """

    # Variable de clase: almacena la única instancia (Singleton)
    _instancia = None

    def __new__(cls):
        """
        __new__ se llama ANTES de __init__ cuando se crea un objeto.
        Aquí implementamos el patrón Singleton.
        """
        if cls._instancia is None:
            # Solo creamos la instancia si no existe
            cls._instancia = super().__new__(cls)
            cls._instancia._inicializado = False  # Bandera para inicializar solo una vez
        return cls._instancia

    def __init__(self):
        """
        Inicializa el sistema de logs.
        Solo se ejecuta la primera vez gracias a la bandera _inicializado.
        """
        if not self._inicializado:
            # Nombre del archivo de logs con fecha del día
            self.archivo = f"software_fj_logs_{datetime.date.today().strftime('%Y%m%d')}.txt"
            self.logs_memoria = []          # Lista para guardar logs en memoria (para la GUI)
            self._inicializado = True       # Marcamos que ya se inicializó
            # Registramos el inicio del sistema
            self.registrar("SISTEMA", "Sistema Software FJ iniciado correctamente")

    def registrar(self, nivel, mensaje, excepcion=None):
        """
        Registra un evento en el archivo de logs y en memoria.

        Parámetros:
        - nivel: tipo de log (INFO, ERROR, ADVERTENCIA, etc.)
        - mensaje: descripción del evento
        - excepcion: objeto Exception si hay un error (opcional)
        """
        # Creamos la marca de tiempo actual
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Construimos la línea del log
        linea = f"[{timestamp}] [{nivel}] {mensaje}"

        # Si hay una excepción, agregamos sus detalles
        if excepcion:
            linea += f" | Excepción: {type(excepcion).__name__}: {str(excepcion)}"

        # Guardamos en la lista de memoria para mostrar en la GUI
        self.logs_memoria.append(linea)

        # Guardamos en el archivo de texto (try/finally garantiza que el archivo se cierre)
        try:
            with open(self.archivo, "a", encoding="utf-8") as f:
                f.write(linea + "\n")          # Escribimos la línea con salto de línea
        except IOError as e:
            # Si no podemos escribir en el archivo, solo lo guardamos en memoria
            self.logs_memoria.append(f"[{timestamp}] [ADVERTENCIA] No se pudo escribir en archivo de logs: {e}")

    def obtener_logs(self, cantidad=50):
        """
        Retorna los últimos N logs registrados.
        Por defecto retorna los últimos 50.
        """
        return self.logs_memoria[-cantidad:]  # Slicing: tomamos los últimos N elementos

# Creé una clase base para organizar y reutilizar características comunes en el sistema.

class Entidad(ABC):
    """
    CLASE ABSTRACTA BASE del sistema.
    Representa cualquier entidad (cliente, servicio, reserva).

    ABC = Abstract Base Class (Clase Base Abstracta)
    No se puede instanciar directamente; hay que heredar de ella.

    Aplica el principio de ABSTRACCIÓN: define la interfaz común
    que todas las entidades del sistema deben implementar.
    """

    # Contador compartido por TODAS las entidades para generar IDs únicos
    _contador_global = 0

    def __init__(self, nombre):
        """
        Constructor de la entidad base.
        Asigna un ID único y registra la fecha de creación.
        """
        # Validamos que el nombre no esté vacío
        if not nombre or not nombre.strip():
            raise SoftwareFJError("El nombre de la entidad no puede estar vacío")

        # Incrementamos el contador global y asignamos ID único
        Entidad._contador_global += 1
        self._id = Entidad._contador_global           # ID único (encapsulado con _)
        self._nombre = nombre.strip()                 # Nombre sin espacios al inicio/fin
        self._fecha_creacion = datetime.datetime.now()  # Fecha y hora de creación
        self._activo = True                           # Por defecto, la entidad está activa

    # PROPIEDADES 
    # Las propiedades permiten acceder a atributos privados de forma controlada

    @property
    def id(self):
        """Getter del ID - solo lectura, no se puede modificar"""
        return self._id

    @property
    def nombre(self):
        """Getter del nombre"""
        return self._nombre

    @property
    def activo(self):
        """Getter del estado activo"""
        return self._activo

    @property
    def fecha_creacion(self):
        """Getter de la fecha de creación"""
        return self._fecha_creacion

    # MÉTODOS ABSTRACTOS 
    # Estos métodos DEBEN ser implementados por las clases hijas

    @abstractmethod
    def describir(self):
        """
        Método abstracto: cada entidad debe describirse a sí misma.
        Las clases hijas OBLIGATORIAMENTE deben implementar este método.
        """
        pass  # 'pass' indica que no hay implementación en la clase abstracta

    @abstractmethod
    def validar(self):
        """
        Método abstracto: cada entidad debe validar sus propios datos.
        Retorna True si los datos son válidos, False si no.
        """
        pass

    # MÉTODOS CONCRETOS 
    # Estos métodos SÍ tienen implementación y pueden ser usados por las hijas

    def desactivar(self):
        """Desactiva la entidad (en lugar de eliminarla)"""
        self._activo = False

    def activar(self):
        """Reactiva una entidad que fue desactivada"""
        self._activo = True

    def __repr__(self):
        """
        Representación técnica del objeto.
        Se muestra cuando hacemos print(objeto) en modo debug.
        """
        return f"{self.__class__.__name__}(id={self._id}, nombre='{self._nombre}')"

# Desarrollé la clase Cliente para gestionar la información y acciones de los usuarios.

class Cliente(Entidad):
    """
    Clase que representa a un cliente de Software FJ.
    Hereda de Entidad y aplica ENCAPSULACIÓN rigurosa
    para proteger los datos personales.

    Principios aplicados:
    - Herencia: hereda de Entidad
    - Encapsulación: atributos privados con _ y propiedades
    - Validación: verifica formato de email, teléfono, etc.
    """

    def __init__(self, nombre, email, telefono, empresa=""):
        """
        Constructor del cliente.

        Parámetros:
        - nombre: nombre completo del cliente
        - email: correo electrónico válido
        - telefono: número de teléfono
        - empresa: empresa donde trabaja (opcional)
        """
        # Primero llamamos al constructor de la clase padre (Entidad)
        super().__init__(nombre)

        # Usamos los setters (propiedades con @setter) para validar antes de asignar
        self.email = email          # Esto llama al setter que valida el email
        self.telefono = telefono    # Esto llama al setter que valida el teléfono
        self._empresa = empresa.strip() if empresa else ""  # Empresa es opcional
        self._reservas = []         # Lista vacía de reservas del cliente
        self._descuento_fidelidad = 0.0  # Descuento por ser cliente frecuente (0-20%)

    # PROPIEDADES CON VALIDACIÓN

    @property
    def email(self):
        """Getter del email"""
        return self._email

    @email.setter
    def email(self, valor):
        """
        Setter del email con validación de formato.
        Se ejecuta automáticamente cuando hacemos: cliente.email = "algo"
        """
        # Verificamos que el email no esté vacío
        if not valor or not valor.strip():
            raise ClienteInvalidoError("email", valor, "El email no puede estar vacío")

        valor = valor.strip().lower()  # Limpiamos y convertimos a minúsculas

        # Validamos el formato con expresión regular
        # El patrón verifica: algo@algo.algo
        patron_email = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(patron_email, valor):
            raise ClienteInvalidoError("email", valor, "Formato de email inválido (use: usuario@dominio.com)")

        self._email = valor  # Si pasa la validación, asignamos el valor

    @property
    def telefono(self):
        """Getter del teléfono"""
        return self._telefono

    @telefono.setter
    def telefono(self, valor):
        """
        Setter del teléfono con validación.
        Acepta solo dígitos, espacios, guiones y el signo +.
        """
        if not valor or not str(valor).strip():
            raise ClienteInvalidoError("telefono", valor, "El teléfono no puede estar vacío")

        valor = str(valor).strip()

        # Verificamos que tenga al menos 7 dígitos (número mínimo válido)
        digitos = re.sub(r'[\s\-\+\(\)]', '', valor)  # Quitamos espacios, guiones, etc.
        if not digitos.isdigit():
            raise ClienteInvalidoError("telefono", valor, "El teléfono solo puede contener números")
        if len(digitos) < 7:
            raise ClienteInvalidoError("telefono", valor, "El teléfono debe tener al menos 7 dígitos")
        if len(digitos) > 15:
            raise ClienteInvalidoError("telefono", valor, "El teléfono no puede tener más de 15 dígitos")

        self._telefono = valor  # Asignamos el valor validado

    @property
    def empresa(self):
        """Getter de la empresa"""
        return self._empresa

    @property
    def descuento_fidelidad(self):
        """Getter del descuento por fidelidad"""
        return self._descuento_fidelidad

    @property
    def total_reservas(self):
        """Retorna el número total de reservas del cliente"""
        return len(self._reservas)

    # MÉTODOS CONCRETOS 

    def agregar_reserva(self, reserva):
        """
        Agrega una reserva a la lista del cliente.
        También actualiza el descuento por fidelidad.
        """
        self._reservas.append(reserva)   # Agregamos la reserva a la lista
        self._actualizar_descuento()     # Recalculamos el descuento

    def _actualizar_descuento(self):
        """
        Método privado (con _) que actualiza el descuento por fidelidad.
        Más reservas = más descuento, hasta un máximo del 20%.
        """
        total = len(self._reservas)      # Contamos las reservas
        if total >= 10:
            self._descuento_fidelidad = 0.20    # 20% para clientes con 10+ reservas
        elif total >= 5:
            self._descuento_fidelidad = 0.10    # 10% para clientes con 5+ reservas
        elif total >= 3:
            self._descuento_fidelidad = 0.05    # 5% para clientes con 3+ reservas
        else:
            self._descuento_fidelidad = 0.0     # Sin descuento para clientes nuevos

    def obtener_reservas(self):
        """Retorna una copia de la lista de reservas (para no exponer la lista original)"""
        return self._reservas.copy()  # .copy() evita que modifiquen la lista interna

    # MÉTODOS ABSTRACTOS IMPLEMENTADOS 

    def describir(self):
        """
        Implementación del método abstracto describir().
        Retorna una descripción completa del cliente.
        """
        desc_empresa = f" ({self._empresa})" if self._empresa else ""
        desc_descuento = f" | Descuento fidelidad: {self._descuento_fidelidad*100:.0f}%" if self._descuento_fidelidad > 0 else ""
        return (f"👤 Cliente #{self._id}: {self._nombre}{desc_empresa}\n"
                f"   📧 {self._email} | 📞 {self._telefono}\n"
                f"   📋 Reservas: {len(self._reservas)}{desc_descuento}")

    def validar(self):
        """
        Implementación del método abstracto validar().
        Verifica que todos los datos del cliente son correctos.
        """
        try:
            # Verificamos cada campo obligatorio
            assert self._nombre, "Nombre vacío"
            assert self._email, "Email vacío"
            assert self._telefono, "Teléfono vacío"
            return True  # Todo está bien
        except AssertionError:
            return False  # Algo falló la validación

# Creé una clase base de servicios para organizar los diferentes tipos de servicios del sistema.

class Servicio(Entidad, ABC):
    """
    CLASE ABSTRACTA que representa un servicio de Software FJ.
    Hereda tanto de Entidad como de ABC (herencia múltiple).

    Define la interfaz común para todos los servicios:
    - Reserva de salas
    - Alquiler de equipos
    - Asesorías especializadas

    Principios aplicados:
    - Abstracción: define métodos que las subclases deben implementar
    - Herencia: hereda de Entidad
    - Polimorfismo: cada servicio calcula costos de forma diferente
    """

    def __init__(self, nombre, precio_base, descripcion=""):
        """
        Constructor del servicio base.

        Parámetros:
        - nombre: nombre del servicio
        - precio_base: precio por unidad (hora, día, sesión)
        - descripcion: descripción detallada del servicio
        """
        # Llamamos al constructor de Entidad
        super().__init__(nombre)

        # Validamos que el precio sea positivo
        if precio_base <= 0:
            raise ServicioInvalidoError(nombre, f"El precio base debe ser positivo, se recibió: {precio_base}")

        self._precio_base = float(precio_base)     # Precio base del servicio
        self._descripcion = descripcion            # Descripción del servicio
        self._disponible = True                    # Estado de disponibilidad
        self._reservas_activas = []                # Lista de reservas activas

    #PROPIEDADES 

    @property
    def precio_base(self):
        """Getter del precio base"""
        return self._precio_base

    @property
    def descripcion(self):
        """Getter de la descripción"""
        return self._descripcion

    @property
    def disponible(self):
        """Getter de la disponibilidad"""
        return self._disponible

    # MÉTODOS ABSTRACTOS (Polimorfismo) 
    # Cada servicio DEBE implementar estos métodos a su manera

    @abstractmethod
    def calcular_costo(self, duracion, **kwargs):
        """
        Calcula el costo total del servicio.
        Cada tipo de servicio lo calcula diferente (POLIMORFISMO).

        Parámetros:
        - duracion: número de horas/días/sesiones
        - **kwargs: parámetros adicionales opcionales (descuentos, extras, etc.)
        """
        pass

    @abstractmethod
    def obtener_tipo(self):
        """Retorna el tipo de servicio (para identificación)"""
        pass

    @abstractmethod
    def validar_duracion(self, duracion):
        """
        Valida si la duración solicitada es válida para este servicio.
        Cada servicio tiene sus propias reglas de duración.
        """
        pass

    # MÉTODOS CONCRETOS

    def verificar_disponibilidad(self):
        """Verifica si el servicio está disponible para nuevas reservas"""
        return self._disponible and self._activo

    def marcar_no_disponible(self):
        """Marca el servicio como no disponible temporalmente"""
        self._disponible = False

    def marcar_disponible(self):
        """Marca el servicio como disponible nuevamente"""
        self._disponible = True

    def calcular_costo_con_iva(self, duracion, tasa_iva=0.19):
        """
        Método SOBRECARGADO: calcula el costo incluyendo IVA.
        Es una variación del método calcular_costo() con parámetro adicional.

        Parámetros:
        - duracion: duración del servicio
        - tasa_iva: porcentaje de IVA (por defecto 19% para Colombia)
        """
        # Validamos que la tasa de IVA sea razonable
        if not (0 <= tasa_iva <= 1):
            raise CalculoError(f"Tasa de IVA inválida: {tasa_iva}. Debe estar entre 0 y 1")

        costo_base = self.calcular_costo(duracion)   # Obtenemos el costo base
        iva = costo_base * tasa_iva                  # Calculamos el IVA
        return {
            "subtotal": costo_base,                  # Costo antes de IVA
            "iva": iva,                              # Valor del IVA
            "total": costo_base + iva,               # Total con IVA
            "tasa_iva": tasa_iva * 100               # Tasa como porcentaje
        }

    def calcular_costo_con_descuento(self, duracion, descuento=0.0):
        """
        Método SOBRECARGADO: calcula el costo con descuento aplicado.
        Variación del calcular_costo() con descuento.

        Parámetros:
        - duracion: duración del servicio
        - descuento: porcentaje de descuento (0.0 a 1.0)
        """
        # Validamos que el descuento sea razonable
        if not (0 <= descuento <= 1):
            raise CalculoError(f"Descuento inválido: {descuento}. Debe estar entre 0 y 1 (0% a 100%)")

        costo_base = self.calcular_costo(duracion)    # Costo sin descuento
        valor_descuento = costo_base * descuento      # Valor a descontar
        costo_final = costo_base - valor_descuento    # Precio final

        return {
            "precio_original": costo_base,            # Precio sin descuento
            "descuento_aplicado": valor_descuento,    # Cuánto se descontó
            "precio_final": costo_final,              # Precio que paga el cliente
            "porcentaje_descuento": descuento * 100   # Descuento como porcentaje
        }

    def validar(self):
        """Implementación del método abstracto validar()"""
        return self._precio_base > 0 and bool(self._nombre)

# Desarrollé servicios especializados utilizando herencia y diferentes comportamientos según cada servicio.

class ReservaSala(Servicio):
    """
    Servicio de RESERVA DE SALAS.
    Hereda de Servicio e implementa todos los métodos abstractos.

    Una sala se reserva por horas y tiene una capacidad máxima.
    Puede incluir servicios adicionales como proyector, coffee break, etc.
    """

    def __init__(self, nombre, precio_hora, capacidad, tiene_proyector=False):
        """
        Constructor de la reserva de sala.

        Parámetros:
        - nombre: nombre de la sala (ej: "Sala Innovación")
        - precio_hora: precio por hora en pesos colombianos
        - capacidad: número máximo de personas
        - tiene_proyector: si la sala tiene proyector incluido
        """
        # Llamamos al constructor del padre (Servicio)
        super().__init__(nombre, precio_hora, f"Sala de reuniones con capacidad para {capacidad} personas")

        # Validamos la capacidad
        if capacidad <= 0:
            raise ServicioInvalidoError(nombre, f"La capacidad debe ser mayor a 0, se recibió: {capacidad}")

        self._capacidad = int(capacidad)                # Capacidad máxima en personas
        self._tiene_proyector = bool(tiene_proyector)   # Si tiene proyector
        self._precio_coffee_break = 15000               # Precio del coffee break por persona

    @property
    def capacidad(self):
        """Getter de la capacidad"""
        return self._capacidad

    @property
    def tiene_proyector(self):
        """Getter de si tiene proyector"""
        return self._tiene_proyector

    def calcular_costo(self, duracion, personas=1, incluir_coffee=False, **kwargs):
        """
        IMPLEMENTACIÓN POLIMÓRFICA del cálculo de costo para salas.

        Fórmula: precio_hora × horas + coffee_break (si aplica)

        Parámetros:
        - duracion: número de horas
        - personas: número de personas asistentes (para coffee break)
        - incluir_coffee: si se incluye coffee break
        - **kwargs: absorbe parámetros adicionales no usados
        """
        # Validamos la duración antes de calcular
        self.validar_duracion(duracion)

        # Calculamos el costo base: precio por hora × número de horas
        costo_base = self._precio_base * duracion

        # Si se incluye coffee break, lo sumamos al costo
        costo_coffee = 0
        if incluir_coffee:
            # Validamos que el número de personas sea válido
            if personas <= 0 or personas > self._capacidad:
                raise CalculoError(
                    f"Número de personas inválido: {personas}. "
                    f"Debe ser entre 1 y {self._capacidad}"
                )
            costo_coffee = self._precio_coffee_break * personas

        return costo_base + costo_coffee  # Retornamos el costo total

    def obtener_tipo(self):
        """Implementación del método abstracto: retorna el tipo de servicio"""
        return "Reserva de Sala"

    def validar_duracion(self, duracion):
        """
        Valida que la duración sea válida para una sala.
        Las salas se reservan en bloques de 1 hora, máximo 8 horas.
        """
        if not isinstance(duracion, (int, float)):
            raise ServicioInvalidoError(self._nombre, f"La duración debe ser un número, se recibió: {type(duracion).__name__}")
        if duracion < 1:
            raise ServicioInvalidoError(self._nombre, "La duración mínima es 1 hora")
        if duracion > 8:
            raise ServicioInvalidoError(self._nombre, "La duración máxima es 8 horas por reserva")
        return True  # Duración válida

    def describir(self):
        """
        SOBRESCRITURA del método describir().
        Muestra información específica de la sala.
        """
        proyector = "✅ Con proyector" if self._tiene_proyector else "❌ Sin proyector"
        return (f"🏢 Sala: {self._nombre}\n"
                f"   👥 Capacidad: {self._capacidad} personas | {proyector}\n"
                f"   💰 Precio: ${self._precio_base:,.0f}/hora\n"
                f"   ☕ Coffee break: ${self._precio_coffee_break:,.0f}/persona")


class AlquilerEquipo(Servicio):
    """
    Servicio de ALQUILER DE EQUIPOS.
    Hereda de Servicio e implementa todos los métodos abstractos.

    Los equipos se alquilan por días y tienen un depósito de garantía.
    """

    def __init__(self, nombre, precio_dia, tipo_equipo, stock=1):
        """
        Constructor del alquiler de equipo.

        Parámetros:
        - nombre: nombre del equipo (ej: "Laptop HP ProBook")
        - precio_dia: precio por día de alquiler
        - tipo_equipo: categoría (laptop, proyector, cámara, etc.)
        - stock: cantidad disponible para alquilar
        """
        # Llamamos al constructor del padre (Servicio)
        super().__init__(nombre, precio_dia, f"Alquiler de {tipo_equipo}: {nombre}")

        # Validamos el stock
        if stock < 0:
            raise ServicioInvalidoError(nombre, f"El stock no puede ser negativo: {stock}")

        self._tipo_equipo = tipo_equipo         # Tipo/categoría del equipo
        self._stock = int(stock)                # Cantidad disponible
        self._stock_inicial = int(stock)        # Stock original (para referencia)
        self._deposito_porcentaje = 0.30        # Depósito = 30% del valor total del alquiler

    @property
    def tipo_equipo(self):
        """Getter del tipo de equipo"""
        return self._tipo_equipo

    @property
    def stock(self):
        """Getter del stock disponible"""
        return self._stock

    def calcular_costo(self, duracion, cantidad=1, **kwargs):
        """
        IMPLEMENTACIÓN POLIMÓRFICA del cálculo de costo para equipos.

        Fórmula: precio_dia x días x cantidad + depósito de garantía

        Parámetros:
        - duracion: número de días de alquiler
        - cantidad: número de unidades a alquilar
        - **kwargs: parámetros adicionales no usados
        """
        # Validamos la duración
        self.validar_duracion(duracion)

        # Validamos la cantidad
        if cantidad <= 0:
            raise CalculoError(f"La cantidad debe ser mayor a 0, se recibió: {cantidad}")
        if cantidad > self._stock:
            raise DisponibilidadError(self._nombre, f"Solo hay {self._stock} unidades disponibles, se solicitaron {cantidad}")

        # Calculamos el costo del alquiler
        costo_alquiler = self._precio_base * duracion * cantidad

        # Calculamos el depósito de garantía (se devuelve al cliente al retornar el equipo)
        deposito = costo_alquiler * self._deposito_porcentaje

        return costo_alquiler + deposito  # Total incluyendo el depósito

    def obtener_tipo(self):
        """Implementación del método abstracto"""
        return "Alquiler de Equipo"

    def validar_duracion(self, duracion):
        """
        Valida la duración para alquiler de equipos.
        El alquiler mínimo es 1 día, máximo 30 días.
        """
        if not isinstance(duracion, (int, float)):
            raise ServicioInvalidoError(self._nombre, f"La duración debe ser un número, se recibió: {type(duracion).__name__}")
        if duracion < 1:
            raise ServicioInvalidoError(self._nombre, "El alquiler mínimo es 1 día")
        if duracion > 30:
            raise ServicioInvalidoError(self._nombre, "El alquiler máximo es 30 días")
        return True

    def reducir_stock(self, cantidad=1):
        """
        Reduce el stock cuando se alquila un equipo.
        Lanza excepción si no hay suficiente stock.
        """
        if self._stock < cantidad:
            raise DisponibilidadError(self._nombre, f"Stock insuficiente: disponible {self._stock}, solicitado {cantidad}")
        self._stock -= cantidad  # Reducimos el stock

    def aumentar_stock(self, cantidad=1):
        """Aumenta el stock cuando se devuelve un equipo"""
        self._stock = min(self._stock + cantidad, self._stock_inicial)  # No supera el stock inicial

    def describir(self):
        """Descripción específica del equipo"""
        return (f"💻 Equipo: {self._nombre}\n"
                f"   🏷️ Tipo: {self._tipo_equipo} | Stock: {self._stock}/{self._stock_inicial}\n"
                f"   💰 Precio: ${self._precio_base:,.0f}/día\n"
                f"   🔒 Depósito garantía: {self._deposito_porcentaje*100:.0f}% del alquiler")


class AsesoriaEspecializada(Servicio):
    """
    Servicio de ASESORÍAS ESPECIALIZADAS.
    Hereda de Servicio e implementa todos los métodos abstractos.

    Las asesorías se cobran por sesiones y pueden incluir material de apoyo.
    El precio varía según la especialidad del asesor.
    """

    # Niveles válidos de asesoría con sus multiplicadores de precio
    NIVELES_VALIDOS = {
        "basico": 1.0,        # Precio base × 1.0
        "intermedio": 1.5,    # Precio base × 1.5
        "avanzado": 2.0,      # Precio base × 2.0
        "experto": 3.0        # Precio base × 3.0
    }

    def __init__(self, nombre, precio_sesion, especialidad, nivel="basico"):
        """
        Constructor de la asesoría especializada.

        Parámetros:
        - nombre: nombre del servicio de asesoría
        - precio_sesion: precio base por sesión
        - especialidad: área de conocimiento (ej: "Desarrollo de Software")
        - nivel: nivel de especialización (basico/intermedio/avanzado/experto)
        """
        # Llamamos al constructor del padre
        super().__init__(nombre, precio_sesion, f"Asesoría especializada en {especialidad}")

        # Validamos que el nivel sea válido
        nivel_lower = nivel.lower()
        if nivel_lower not in self.NIVELES_VALIDOS:
            raise ServicioInvalidoError(
                nombre,
                f"Nivel inválido: '{nivel}'. Debe ser uno de: {', '.join(self.NIVELES_VALIDOS.keys())}"
            )

        self._especialidad = especialidad          # Área de especialización
        self._nivel = nivel_lower                  # Nivel de la asesoría
        self._incluir_material = False             # Si incluye material de apoyo
        self._precio_material = 25000              # Precio del material de apoyo

    @property
    def especialidad(self):
        """Getter de la especialidad"""
        return self._especialidad

    @property
    def nivel(self):
        """Getter del nivel"""
        return self._nivel

    def calcular_costo(self, duracion, incluir_material=False, **kwargs):
        """
        IMPLEMENTACIÓN POLIMÓRFICA del cálculo de costo para asesorías.

        Fórmula: precio_sesion × multiplicador_nivel × número_sesiones + material

        Parámetros:
        - duracion: número de sesiones
        - incluir_material: si se incluye material de apoyo
        - **kwargs: parámetros adicionales no usados
        """
        # Validamos la duración (número de sesiones)
        self.validar_duracion(duracion)

        # Obtenemos el multiplicador según el nivel de la asesoría
        multiplicador = self.NIVELES_VALIDOS[self._nivel]

        # Calculamos el costo de las sesiones
        costo_sesiones = self._precio_base * multiplicador * duracion

        # Agregamos el costo del material si se solicita
        costo_material = self._precio_material if incluir_material else 0

        return costo_sesiones + costo_material  # Costo total

    def obtener_tipo(self):
        """Implementación del método abstracto"""
        return "Asesoría Especializada"

    def validar_duracion(self, duracion):
        """
        Valida el número de sesiones.
        Mínimo 1 sesión, máximo 20 sesiones por reserva.
        """
        if not isinstance(duracion, (int, float)):
            raise ServicioInvalidoError(self._nombre, f"La duración debe ser un número")
        if duracion < 1:
            raise ServicioInvalidoError(self._nombre, "Se requiere mínimo 1 sesión")
        if duracion > 20:
            raise ServicioInvalidoError(self._nombre, "El máximo es 20 sesiones por reserva")
        return True

    def describir(self):
        """Descripción específica de la asesoría"""
        multiplicador = self.NIVELES_VALIDOS[self._nivel]
        precio_real = self._precio_base * multiplicador
        return (f"🎓 Asesoría: {self._nombre}\n"
                f"   📚 Especialidad: {self._especialidad} | Nivel: {self._nivel.capitalize()}\n"
                f"   💰 Precio: ${precio_real:,.0f}/sesión\n"
                f"   📖 Material de apoyo: ${self._precio_material:,.0f} (opcional)")

# Creé la clase Reserva para administrar las reservas realizadas en el sistema.

class Reserva(Entidad):
    """
    Clase que representa una RESERVA en el sistema Software FJ.
    Integra un cliente con un servicio y gestiona su ciclo de vida.

    Estados posibles de una reserva:
    - PENDIENTE: creada pero no confirmada
    - CONFIRMADA: reserva aprobada y activa
    - CANCELADA: reserva anulada
    - COMPLETADA: servicio ya fue prestado
    """

    # Constantes para los estados de la reserva
    ESTADO_PENDIENTE = "PENDIENTE"
    ESTADO_CONFIRMADA = "CONFIRMADA"
    ESTADO_CANCELADA = "CANCELADA"
    ESTADO_COMPLETADA = "COMPLETADA"

    def __init__(self, cliente, servicio, duracion, fecha_servicio=None):
        """
        Constructor de la reserva.

        Parámetros:
        - cliente: objeto Cliente que hace la reserva
        - servicio: objeto Servicio que se está reservando
        - duracion: duración del servicio (horas/días/sesiones)
        - fecha_servicio: fecha programada (opcional, por defecto mañana)
        """
        # Construimos el nombre de la reserva para la clase padre
        nombre_reserva = f"Reserva_{cliente.nombre}_{servicio.nombre}"
        super().__init__(nombre_reserva)

        # ── Validaciones antes de crear la reserva ──

        # Verificamos que el cliente sea una instancia válida de Cliente
        if not isinstance(cliente, Cliente):
            raise ReservaError("El cliente debe ser una instancia de la clase Cliente")

        # Verificamos que el servicio sea válido
        if not isinstance(servicio, Servicio):
            raise ReservaError("El servicio debe ser una instancia de la clase Servicio")

        # Verificamos que el cliente esté activo
        if not cliente.activo:
            raise ReservaError(f"El cliente '{cliente.nombre}' está inactivo y no puede hacer reservas")

        # Verificamos disponibilidad del servicio
        if not servicio.verificar_disponibilidad():
            raise DisponibilidadError(servicio.nombre)

        # Validamos la duración usando el método del servicio específico
        servicio.validar_duracion(duracion)

        # Asignamos todos los atributos
        self._cliente = cliente                   # Referencia al cliente
        self._servicio = servicio                 # Referencia al servicio
        self._duracion = duracion                 # Duración solicitada
        self._estado = self.ESTADO_PENDIENTE      # Estado inicial siempre es PENDIENTE
        self._costo_calculado = 0.0               # Se calcula al confirmar
        self._notas = ""                          # Notas adicionales opcionales

        # Si no se especifica fecha, programamos para mañana
        if fecha_servicio is None:
            self._fecha_servicio = datetime.date.today() + datetime.timedelta(days=1)
        else:
            self._fecha_servicio = fecha_servicio

        self._fecha_confirmacion = None           # Se llenará al confirmar
        self._fecha_cancelacion = None            # Se llenará al cancelar

    # ──── PROPIEDADES ────

    @property
    def cliente(self):
        """Getter del cliente"""
        return self._cliente

    @property
    def servicio(self):
        """Getter del servicio"""
        return self._servicio

    @property
    def estado(self):
        """Getter del estado"""
        return self._estado

    @property
    def costo(self):
        """Getter del costo calculado"""
        return self._costo_calculado

    @property
    def duracion(self):
        """Getter de la duración"""
        return self._duracion

    @property
    def fecha_servicio(self):
        """Getter de la fecha del servicio"""
        return self._fecha_servicio

    # MÉTODOS DE GESTIÓN DE LA RESERVA 

    def confirmar(self, descuento_adicional=0.0):
        """
        CONFIRMA la reserva y calcula el costo final.
        Solo se puede confirmar si está en estado PENDIENTE.

        Parámetros:
        - descuento_adicional: descuento extra a aplicar (0.0 a 1.0)

        Manejo de excepciones: try/except/else/finally
        """
        # Verificamos que la reserva esté en estado correcto para confirmar
        if self._estado != self.ESTADO_PENDIENTE:
            raise ReservaError(
                f"No se puede confirmar: estado actual es '{self._estado}', se requiere '{self.ESTADO_PENDIENTE}'",
                self._id
            )

        logs = SistemaLogs()  # Obtenemos la instancia del sistema de logs

        try:
            # Intentamos calcular el costo
            # Primero calculamos el costo base del servicio
            costo_base = self._servicio.calcular_costo(self._duracion)

            # Calculamos el descuento total (fidelidad del cliente + descuento adicional)
            descuento_total = self._cliente.descuento_fidelidad + descuento_adicional

            # Nos aseguramos de que el descuento no supere el 50%
            descuento_total = min(descuento_total, 0.50)

            # Validamos el descuento adicional
            if descuento_adicional < 0 or descuento_adicional > 1:
                raise CalculoError(f"Descuento inválido: {descuento_adicional}")

            # Calculamos el costo final con descuento
            resultado = self._servicio.calcular_costo_con_descuento(self._duracion, descuento_total)
            self._costo_calculado = resultado["precio_final"]

        except CalculoError as e:
            # Si hay error en el cálculo, encadenamos la excepción con más contexto
            logs.registrar("ERROR", f"Error calculando costo de reserva #{self._id}", e)
            raise ReservaError(f"Error en cálculo de costo: {str(e)}", self._id) from e  # Encadenamiento de excepciones

        except ServicioInvalidoError as e:
            # Error específico del servicio
            logs.registrar("ERROR", f"Servicio inválido en reserva #{self._id}", e)
            raise ReservaError(f"Servicio no válido: {str(e)}", self._id) from e

        except Exception as e:
            # Capturamos cualquier otro error inesperado
            logs.registrar("ERROR", f"Error inesperado confirmando reserva #{self._id}", e)
            raise ReservaError(f"Error inesperado al confirmar: {str(e)}", self._id)

        else:
            # El bloque 'else' se ejecuta SOLO si no hubo excepciones
            self._estado = self.ESTADO_CONFIRMADA             # Cambiamos el estado
            self._fecha_confirmacion = datetime.datetime.now() # Registramos cuando se confirmó
            self._cliente.agregar_reserva(self)               # Asociamos al cliente
            logs.registrar("INFO", f"Reserva #{self._id} confirmada. Costo: ${self._costo_calculado:,.0f}")

        finally:
            # El bloque 'finally' SIEMPRE se ejecuta, haya o no error
            # Útil para liberar recursos o registrar el fin de la operación
            logs.registrar("DEBUG", f"Proceso de confirmación de reserva #{self._id} finalizado")

    def cancelar(self, motivo="Sin motivo especificado"):
        """
        CANCELA la reserva.
        Solo se puede cancelar si está en estado PENDIENTE o CONFIRMADA.

        Parámetros:
        - motivo: razón de la cancelación
        """
        # Verificamos que se pueda cancelar
        if self._estado == self.ESTADO_CANCELADA:
            raise ReservaError(f"La reserva ya estaba cancelada", self._id)

        if self._estado == self.ESTADO_COMPLETADA:
            raise ReservaError(f"No se puede cancelar una reserva ya completada", self._id)

        # Cambiamos el estado a cancelado
        self._estado = self.ESTADO_CANCELADA
        self._fecha_cancelacion = datetime.datetime.now()
        self._notas = f"Cancelada: {motivo}"

        # Registramos en logs
        SistemaLogs().registrar("INFO", f"Reserva #{self._id} cancelada. Motivo: {motivo}")

    def completar(self):
        """
        Marca la reserva como COMPLETADA.
        Solo se puede completar si está CONFIRMADA.
        """
        if self._estado != self.ESTADO_CONFIRMADA:
            raise ReservaError(
                f"Solo se pueden completar reservas confirmadas. Estado actual: {self._estado}",
                self._id
            )

        self._estado = self.ESTADO_COMPLETADA
        SistemaLogs().registrar("INFO", f"Reserva #{self._id} marcada como completada")

    # MÉTODOS ABSTRACTOS IMPLEMENTADOS

    def describir(self):
        """Descripción completa de la reserva"""
        estado_emoji = {
            self.ESTADO_PENDIENTE: "⏳",
            self.ESTADO_CONFIRMADA: "✅",
            self.ESTADO_CANCELADA: "❌",
            self.ESTADO_COMPLETADA: "🏁"
        }
        emoji = estado_emoji.get(self._estado, "❓")

        return (f"{emoji} Reserva #{self._id} [{self._estado}]\n"
                f"   👤 Cliente: {self._cliente.nombre}\n"
                f"   🔧 Servicio: {self._servicio.nombre} ({self._servicio.obtener_tipo()})\n"
                f"   ⏱️ Duración: {self._duracion} | 📅 Fecha: {self._fecha_servicio}\n"
                f"   💰 Costo: ${self._costo_calculado:,.0f}")

    def validar(self):
        """Valida que la reserva tenga todos los datos correctos"""
        return (self._cliente is not None and
                self._servicio is not None and
                self._duracion > 0 and
                self._estado in [self.ESTADO_PENDIENTE, self.ESTADO_CONFIRMADA,
                                  self.ESTADO_CANCELADA, self.ESTADO_COMPLETADA])

# Desarrollé el gestor principal para controlar y coordinar el funcionamiento del sistema.

class SistemaGestionFJ:
    """
    Clase principal que gestiona todas las operaciones de Software FJ.
    Actúa como el controlador central del sistema.

    Contiene las listas de clientes, servicios y reservas,
    y expone métodos para realizar todas las operaciones del negocio.
    """

    def __init__(self):
        """Inicializa el sistema con listas vacías"""
        self._clientes = []      # Lista de todos los clientes registrados
        self._servicios = []     # Lista de todos los servicios disponibles
        self._reservas = []      # Lista de todas las reservas del sistema
        self._logs = SistemaLogs()  # Sistema de logs (Singleton)
        self._logs.registrar("INFO", "Sistema de Gestión Software FJ inicializado")

    # GESTIÓN DE CLIENTES

    def registrar_cliente(self, nombre, email, telefono, empresa=""):
        """
        Registra un nuevo cliente en el sistema.

        Parámetros:
        - nombre, email, telefono, empresa: datos del cliente

        Maneja excepciones de validación con try/except
        """
        try:
            # Intentamos crear el cliente (puede lanzar ClienteInvalidoError)
            cliente = Cliente(nombre, email, telefono, empresa)

            # Verificamos si ya existe un cliente con ese email
            for c in self._clientes:
                if c.email == cliente.email:
                    raise ClienteInvalidoError("email", email, "Ya existe un cliente con este email")

            # Si todo está bien, agregamos el cliente a la lista
            self._clientes.append(cliente)
            self._logs.registrar("INFO", f"Cliente registrado: {cliente.nombre} ({cliente.email})")
            return cliente  # Retornamos el objeto cliente creado

        except ClienteInvalidoError as e:
            # Capturamos errores de validación del cliente
            self._logs.registrar("ERROR", f"Error registrando cliente '{nombre}'", e)
            raise  # Re-lanzamos la excepción para que la GUI la maneje

        except Exception as e:
            # Capturamos cualquier otro error inesperado
            self._logs.registrar("ERROR", f"Error inesperado registrando cliente '{nombre}'", e)
            raise SoftwareFJError(f"Error inesperado: {str(e)}") from e

    def buscar_cliente(self, criterio):
        """
        Busca clientes por nombre, email o empresa.
        Retorna una lista de clientes que coinciden con el criterio.
        """
        criterio_lower = criterio.lower().strip()  # Convertimos a minúsculas para comparar
        resultados = []

        for cliente in self._clientes:
            # Buscamos en nombre, email y empresa
            if (criterio_lower in cliente.nombre.lower() or
                    criterio_lower in cliente.email.lower() or
                    criterio_lower in cliente.empresa.lower()):
                resultados.append(cliente)

        return resultados  # Lista de clientes encontrados (puede estar vacía)

    #  GESTIÓN DE SERVICIOS

    def agregar_servicio(self, servicio):
        """
        Agrega un nuevo servicio al catálogo del sistema.

        Parámetros:
        - servicio: objeto Servicio (ReservaSala, AlquilerEquipo, o AsesoriaEspecializada)
        """
        try:
            # Validamos que sea realmente un servicio
            if not isinstance(servicio, Servicio):
                raise ServicioInvalidoError("Desconocido", "El objeto no es una instancia de Servicio")

            # Verificamos que el servicio sea válido
            if not servicio.validar():
                raise ServicioInvalidoError(servicio.nombre, "Los datos del servicio no son válidos")

            self._servicios.append(servicio)  # Agregamos a la lista
            self._logs.registrar("INFO", f"Servicio agregado: {servicio.nombre} ({servicio.obtener_tipo()})")
            return servicio

        except ServicioInvalidoError as e:
            self._logs.registrar("ERROR", "Error agregando servicio", e)
            raise

    def buscar_servicio(self, tipo=None):
        """
        Busca servicios por tipo.

        Parámetros:
        - tipo: tipo de servicio a buscar (None = todos)

        Retorna lista de servicios disponibles del tipo especificado.
        """
        if tipo is None:
            # Si no se especifica tipo, retornamos todos los servicios activos
            return [s for s in self._servicios if s.activo and s.disponible]

        # Filtramos por tipo de servicio (insensible a mayúsculas)
        tipo_lower = tipo.lower()
        return [s for s in self._servicios
                if s.activo and s.disponible and tipo_lower in s.obtener_tipo().lower()]

    # GESTIÓN DE RESERVAS

    def crear_reserva(self, cliente_id, servicio_id, duracion):
        """
        Crea una nueva reserva en el sistema.

        Parámetros:
        - cliente_id: ID del cliente que hace la reserva
        - servicio_id: ID del servicio a reservar
        - duracion: duración solicitada

        Usa try/except para manejar múltiples tipos de errores.
        """
        cliente = None   # Inicializamos en None por si no se encuentra
        servicio = None  # Inicializamos en None por si no se encuentra

        try:
            # Buscamos el cliente por ID
            for c in self._clientes:
                if c.id == cliente_id:
                    cliente = c
                    break  # Salimos del bucle cuando lo encontramos

            # Si no encontramos el cliente, lanzamos excepción
            if cliente is None:
                raise ReservaError(f"Cliente con ID {cliente_id} no encontrado en el sistema")

            # Buscamos el servicio por ID
            for s in self._servicios:
                if s.id == servicio_id:
                    servicio = s
                    break

            # Si no encontramos el servicio, lanzamos excepción
            if servicio is None:
                raise ReservaError(f"Servicio con ID {servicio_id} no encontrado en el sistema")

            # Creamos la reserva (puede lanzar ReservaError o DisponibilidadError)
            reserva = Reserva(cliente, servicio, duracion)

            # Intentamos confirmar automáticamente
            reserva.confirmar()

            # Si todo salió bien, guardamos la reserva
            self._reservas.append(reserva)
            self._logs.registrar("INFO", f"Reserva creada y confirmada: #{reserva.id}")
            return reserva  # Retornamos la reserva creada

        except (ReservaError, DisponibilidadError) as e:
            # Errores específicos del negocio
            self._logs.registrar("ERROR", "Error en proceso de reserva", e)
            raise

        except ServicioInvalidoError as e:
            # Error en el servicio
            self._logs.registrar("ERROR", "Servicio inválido durante reserva", e)
            raise ReservaError(f"Problema con el servicio: {str(e)}") from e

        except Exception as e:
            # Cualquier otro error inesperado
            self._logs.registrar("ERROR", "Error inesperado en reserva", e)
            raise SoftwareFJError(f"Error inesperado al crear reserva: {str(e)}") from e

        finally:
            # Siempre registramos que el proceso terminó
            cliente_nombre = cliente.nombre if cliente else f"ID:{cliente_id}"
            self._logs.registrar("DEBUG", f"Proceso de reserva para {cliente_nombre} finalizado")

    def cancelar_reserva(self, reserva_id, motivo=""):
        """
        Cancela una reserva existente.

        Parámetros:
        - reserva_id: ID de la reserva a cancelar
        - motivo: razón de la cancelación
        """
        try:
            # Buscamos la reserva por ID
            reserva = None
            for r in self._reservas:
                if r.id == reserva_id:
                    reserva = r
                    break

            if reserva is None:
                raise ReservaError(f"Reserva con ID {reserva_id} no encontrada")

            # Intentamos cancelar
            reserva.cancelar(motivo if motivo else "Cancelada por el sistema")
            return reserva

        except ReservaError as e:
            self._logs.registrar("ERROR", f"Error cancelando reserva #{reserva_id}", e)
            raise

    # PROPIEDADES DE ACCESO A LISTAS 

    @property
    def clientes(self):
        """Retorna copia de la lista de clientes"""
        return self._clientes.copy()

    @property
    def servicios(self):
        """Retorna copia de la lista de servicios"""
        return self._servicios.copy()

    @property
    def reservas(self):
        """Retorna copia de la lista de reservas"""
        return self._reservas.copy()

    def obtener_estadisticas(self):
        """
        Calcula y retorna estadísticas generales del sistema.
        Demuestra el uso de listas y cálculos con manejo de excepciones.
        """
        try:
            # Contamos reservas por estado
            confirmadas = sum(1 for r in self._reservas if r.estado == Reserva.ESTADO_CONFIRMADA)
            canceladas = sum(1 for r in self._reservas if r.estado == Reserva.ESTADO_CANCELADA)
            completadas = sum(1 for r in self._reservas if r.estado == Reserva.ESTADO_COMPLETADA)

            # Calculamos ingresos totales (solo reservas confirmadas y completadas)
            ingresos = sum(r.costo for r in self._reservas
                          if r.estado in [Reserva.ESTADO_CONFIRMADA, Reserva.ESTADO_COMPLETADA])

            return {
                "total_clientes": len(self._clientes),
                "total_servicios": len(self._servicios),
                "total_reservas": len(self._reservas),
                "reservas_confirmadas": confirmadas,
                "reservas_canceladas": canceladas,
                "reservas_completadas": completadas,
                "ingresos_totales": ingresos
            }
        except Exception as e:
            self._logs.registrar("ERROR", "Error calculando estadísticas", e)
            return {}  # Retornamos diccionario vacío si hay error
        
# Diseñé una interfaz gráfica para facilitar el uso del sistema de manera visual e interactiva. (GUI con Tkinter)

class AplicacionFJ:
    """
    Clase principal de la interfaz gráfica de usuario (GUI).
    Usa Tkinter para crear una aplicación de escritorio con múltiples pestañas.

    La GUI permite:
    - Registrar clientes
    - Ver y gestionar servicios
    - Crear y gestionar reservas
    - Ver logs del sistema
    - Ver estadísticas
    """

    def __init__(self, root):
        """
        Constructor de la aplicación GUI.

        Parámetros:
        - root: ventana principal de Tkinter
        """
        self.root = root                              # Ventana principal
        self.root.title("Software FJ - Sistema de Gestión de Reservas")  # Título
        self.root.geometry("1100x750")                # Tamaño inicial de la ventana
        self.root.minsize(900, 600)                   # Tamaño mínimo

        # Colores corporativos de Software FJ
        self.COLOR_PRIMARIO = "#1a1a2e"               # Azul oscuro (fondo principal)
        self.COLOR_SECUNDARIO = "#16213e"             # Azul medio
        self.COLOR_ACENTO = "#0f3460"                 # Azul profundo
        self.COLOR_VERDE = "#00b4d8"                  # Cian (botones de acción)
        self.COLOR_TEXTO = "#e0e0e0"                  # Gris claro (texto)
        self.COLOR_BLANCO = "#ffffff"                 # Blanco puro
        self.COLOR_ERROR = "#e63946"                  # Rojo (errores)
        self.COLOR_EXITO = "#2ec4b6"                  # Verde azulado (éxito)
        self.COLOR_ADVERTENCIA = "#ffd166"            # Amarillo (advertencias)

        # Configuramos el fondo de la ventana principal
        self.root.configure(bg=self.COLOR_PRIMARIO)

        # Inicializamos el sistema de gestión
        self.sistema = SistemaGestionFJ()

        # Cargamos datos de demostración
        self._cargar_datos_demo()

        # Construimos la interfaz gráfica
        self._construir_gui()

    def _cargar_datos_demo(self):
        """
        Carga datos de demostración para mostrar el sistema funcionando.
        Simula las 10+ operaciones requeridas (válidas e inválidas).
        """
        logs = SistemaLogs()
        logs.registrar("INFO", "=== INICIO DE SIMULACIÓN DE OPERACIONES DE DEMOSTRACIÓN ===")

        # Registrar servicios válidos
        logs.registrar("INFO", "OPERACIÓN 1: Registrando servicios válidos")
        try:
            sala1 = ReservaSala("Sala Innovación A", 80000, 10, tiene_proyector=True)
            sala2 = ReservaSala("Sala Creatividad B", 60000, 6, tiene_proyector=False)
            equipo1 = AlquilerEquipo("Laptop Dell XPS", 35000, "Laptop", stock=3)
            equipo2 = AlquilerEquipo("Proyector Epson 4K", 45000, "Proyector", stock=2)
            asesoria1 = AsesoriaEspecializada("Consultoría en Cloud", 120000, "Arquitectura Cloud", "avanzado")
            asesoria2 = AsesoriaEspecializada("Scrum y Agile", 80000, "Metodologías Ágiles", "intermedio")

            # Agregamos los servicios al sistema
            for servicio in [sala1, sala2, equipo1, equipo2, asesoria1, asesoria2]:
                self.sistema.agregar_servicio(servicio)

            logs.registrar("INFO", "✅ Servicios registrados correctamente")
        except Exception as e:
            logs.registrar("ERROR", "Error registrando servicios de demostración", e)

        # OPERACIÓN 2: Registrar clientes válidos
        logs.registrar("INFO", "OPERACIÓN 2: Registrando clientes válidos")
        try:
            self.sistema.registrar_cliente("Ana García López", "ana.garcia@techcorp.com", "3001234567", "TechCorp S.A.S")
            self.sistema.registrar_cliente("Carlos Mendoza", "cmendoza@startup.io", "3119876543", "Startup.io")
            self.sistema.registrar_cliente("María Fernández", "mfernandez@gmail.com", "6017654321")
            logs.registrar("INFO", "✅ Clientes registrados correctamente")
        except Exception as e:
            logs.registrar("ERROR", "Error registrando clientes de demostración", e)

        # OPERACIÓN 3: Intentar registrar cliente con email inválido
        logs.registrar("INFO", "OPERACIÓN 3: Intentando registrar cliente con email inválido (debe fallar)")
        try:
            self.sistema.registrar_cliente("Pedro Inválido", "esto-no-es-email", "3001111111")
            logs.registrar("ERROR", "⚠️ No se detectó el email inválido (esto no debería pasar)")
        except ClienteInvalidoError as e:
            logs.registrar("ADVERTENCIA", f"✅ Error capturado correctamente: {e}")

        # OPERACIÓN 4: Intentar registrar cliente con teléfono inválido
        logs.registrar("INFO", "OPERACIÓN 4: Intentando registrar cliente con teléfono inválido")
        try:
            self.sistema.registrar_cliente("Luis Error", "luis@test.com", "abc123")
        except ClienteInvalidoError as e:
            logs.registrar("ADVERTENCIA", f"✅ Error de teléfono capturado: {e}")

        # OPERACIÓN 5: Crear servicio con precio negativo 
        logs.registrar("INFO", "OPERACIÓN 5: Intentando crear servicio con precio negativo (debe fallar)")
        try:
            servicio_invalido = ReservaSala("Sala Gratis", -5000, 10)
            self.sistema.agregar_servicio(servicio_invalido)
        except ServicioInvalidoError as e:
            logs.registrar("ADVERTENCIA", f"✅ Error de precio negativo capturado: {e}")

        # OPERACIÓN 6: Crear reservas válidas 
        logs.registrar("INFO", "OPERACIÓN 6: Creando reservas válidas")
        try:
            clientes = self.sistema.clientes
            servicios = self.sistema.servicios

            if len(clientes) > 0 and len(servicios) > 0:
                # Reserva 1: Sala de innovación por 3 horas
                self.sistema.crear_reserva(clientes[0].id, servicios[0].id, 3)
                # Reserva 2: Alquiler de laptop por 2 días
                if len(servicios) > 2:
                    self.sistema.crear_reserva(clientes[1].id, servicios[2].id, 2)
                # Reserva 3: Asesoría en cloud por 2 sesiones
                if len(clientes) > 2 and len(servicios) > 4:
                    self.sistema.crear_reserva(clientes[2].id, servicios[4].id, 2)
            logs.registrar("INFO", "✅ Reservas creadas correctamente")
        except Exception as e:
            logs.registrar("ERROR", "Error creando reservas de demostración", e)

        # OPERACIÓN 7: Intentar reserva con duración inválida 
        logs.registrar("INFO", "OPERACIÓN 7: Intentando reserva con duración inválida (debe fallar)")
        try:
            clientes = self.sistema.clientes
            servicios = self.sistema.servicios
            if clientes and servicios:
                self.sistema.crear_reserva(clientes[0].id, servicios[0].id, 99)  # 99 horas es inválido
        except (ReservaError, ServicioInvalidoError) as e:
            logs.registrar("ADVERTENCIA", f"✅ Error de duración capturado: {e}")

        # OPERACIÓN 8: Intentar reserva con ID de cliente inexistente
        logs.registrar("INFO", "OPERACIÓN 8: Intentando reserva con cliente inexistente (debe fallar)")
        try:
            servicios = self.sistema.servicios
            if servicios:
                self.sistema.crear_reserva(9999, servicios[0].id, 2)  # ID 9999 no existe
        except ReservaError as e:
            logs.registrar("ADVERTENCIA", f"✅ Error de cliente inexistente capturado: {e}")

        # OPERACIÓN 9: Intentar registrar cliente con email duplicado
        logs.registrar("INFO", "OPERACIÓN 9: Intentando registrar cliente con email duplicado")
        try:
            self.sistema.registrar_cliente("Ana Copia", "ana.garcia@techcorp.com", "3002222222")
        except ClienteInvalidoError as e:
            logs.registrar("ADVERTENCIA", f"✅ Error de email duplicado capturado: {e}")

        # OPERACIÓN 10: Cancelar una reserva existente
        logs.registrar("INFO", "OPERACIÓN 10: Cancelando una reserva existente")
        try:
            reservas = self.sistema.reservas
            if reservas:
                self.sistema.cancelar_reserva(reservas[-1].id, "Cliente solicita cambio de fecha")
                logs.registrar("INFO", "✅ Reserva cancelada correctamente")
        except ReservaError as e:
            logs.registrar("ERROR", f"Error cancelando reserva: {e}")

        # OPERACIÓN 11: Crear servicio con nivel inválido 
        logs.registrar("INFO", "OPERACIÓN 11: Creando asesoría con nivel inválido (debe fallar)")
        try:
            AsesoriaEspecializada("Asesoría Ninja", 100000, "Kung Fu del código", "ninja")
        except ServicioInvalidoError as e:
            logs.registrar("ADVERTENCIA", f"✅ Error de nivel inválido capturado: {e}")

        # OPERACIÓN 12: Intentar crear servicio con capacidad negativa
        logs.registrar("INFO", "OPERACIÓN 12: Sala con capacidad cero (debe fallar)")
        try:
            ReservaSala("Sala Fantasma", 50000, 0)
        except ServicioInvalidoError as e:
            logs.registrar("ADVERTENCIA", f"✅ Error de capacidad capturado: {e}")

        logs.registrar("INFO", "=== FIN DE SIMULACIÓN: 12 OPERACIONES COMPLETADAS ===")

    def _construir_gui(self):
        """
        Construye todos los elementos de la interfaz gráfica.
        Organiza la ventana con un header, panel de navegación y área de contenido.
        """
        # HEADER
        frame_header = tk.Frame(self.root, bg=self.COLOR_ACENTO, height=70)
        frame_header.pack(fill="x")                 # Se extiende horizontalmente
        frame_header.pack_propagate(False)           # Fijamos la altura

        # Logo y título en el header
        tk.Label(
            frame_header,
            text="⚡ SOFTWARE FJ",
            font=("Segoe UI", 22, "bold"),
            bg=self.COLOR_ACENTO,
            fg=self.COLOR_VERDE
        ).pack(side="left", padx=20, pady=15)

        # Subtítulo
        tk.Label(
            frame_header,
            text="Sistema Integral de Gestión de Reservas",
            font=("Segoe UI", 11),
            bg=self.COLOR_ACENTO,
            fg=self.COLOR_TEXTO
        ).pack(side="left", padx=5, pady=15)

        # Fecha y hora en el header
        self.lbl_hora = tk.Label(
            frame_header,
            text="",
            font=("Segoe UI", 10),
            bg=self.COLOR_ACENTO,
            fg=self.COLOR_TEXTO
        )
        self.lbl_hora.pack(side="right", padx=20)
        self._actualizar_hora()  # Iniciamos el reloj

        # CONTENEDOR PRINCIPAL
        frame_main = tk.Frame(self.root, bg=self.COLOR_PRIMARIO)
        frame_main.pack(fill="both", expand=True)

        # PANEL LATERAL DE NAVEGACIÓN 
        frame_nav = tk.Frame(frame_main, bg=self.COLOR_SECUNDARIO, width=180)
        frame_nav.pack(side="left", fill="y")
        frame_nav.pack_propagate(False)  # Fijamos el ancho

        # Título del panel de navegación
        tk.Label(
            frame_nav,
            text="MENÚ",
            font=("Segoe UI", 10, "bold"),
            bg=self.COLOR_SECUNDARIO,
            fg=self.COLOR_VERDE
        ).pack(pady=(20, 5))

        # Separador visual
        ttk.Separator(frame_nav, orient="horizontal").pack(fill="x", padx=10, pady=5)

        # Botones de navegación
        # Cada botón llama a una función diferente que muestra la sección correspondiente
        botones_nav = [
            ("🏠 Dashboard", self._mostrar_dashboard),
            ("👥 Clientes", self._mostrar_clientes),
            ("🔧 Servicios", self._mostrar_servicios),
            ("📋 Reservas", self._mostrar_reservas),
            ("📊 Estadísticas", self._mostrar_estadisticas),
            ("📝 Logs", self._mostrar_logs),
        ]

        for texto, comando in botones_nav:
            btn = tk.Button(
                frame_nav,
                text=texto,
                command=comando,
                font=("Segoe UI", 10),
                bg=self.COLOR_ACENTO,
                fg=self.COLOR_TEXTO,
                activebackground=self.COLOR_VERDE,
                activeforeground=self.COLOR_PRIMARIO,
                relief="flat",              # Sin borde
                cursor="hand2",             # Cursor de mano al pasar sobre el botón
                padx=10, pady=10,
                anchor="w"                  # Texto alineado a la izquierda
            )
            btn.pack(fill="x", padx=10, pady=3)  # Se extiende al ancho del panel

        # ── ÁREA DE CONTENIDO PRINCIPAL ──
        self.frame_contenido = tk.Frame(frame_main, bg=self.COLOR_PRIMARIO)
        self.frame_contenido.pack(side="right", fill="both", expand=True)

        # Mostramos el dashboard al iniciar
        self._mostrar_dashboard()

    def _actualizar_hora(self):
        """Actualiza el reloj en el header cada segundo"""
        hora_actual = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        self.lbl_hora.config(text=hora_actual)
        # Programamos la próxima actualización en 1000ms (1 segundo)
        self.root.after(1000, self._actualizar_hora)

    def _limpiar_contenido(self):
        """Elimina todos los widgets del área de contenido antes de mostrar una nueva sección"""
        for widget in self.frame_contenido.winfo_children():
            widget.destroy()  # Destruimos cada widget hijo

    def _crear_titulo_seccion(self, texto, subtexto=""):
        """
        Crea el título estilizado para cada sección.
        Retorna el frame creado para que se pueda configurar más.
        """
        frame_titulo = tk.Frame(self.frame_contenido, bg=self.COLOR_SECUNDARIO)
        frame_titulo.pack(fill="x", padx=20, pady=(20, 10))

        tk.Label(
            frame_titulo,
            text=texto,
            font=("Segoe UI", 18, "bold"),
            bg=self.COLOR_SECUNDARIO,
            fg=self.COLOR_VERDE
        ).pack(side="left", padx=15, pady=10)

        if subtexto:
            tk.Label(
                frame_titulo,
                text=subtexto,
                font=("Segoe UI", 10),
                bg=self.COLOR_SECUNDARIO,
                fg=self.COLOR_TEXTO
            ).pack(side="left", padx=5)

        return frame_titulo

    def _mostrar_dashboard(self):
        """
        Muestra el panel de inicio con un resumen del sistema.
        """
        self._limpiar_contenido()  # Limpiamos el contenido anterior
        self._crear_titulo_seccion("🏠 Dashboard", "Bienvenido a Software FJ")

        # Obtenemos las estadísticas del sistema
        stats = self.sistema.obtener_estadisticas()

        # ── TARJETAS DE ESTADÍSTICAS ──
        frame_cards = tk.Frame(self.frame_contenido, bg=self.COLOR_PRIMARIO)
        frame_cards.pack(fill="x", padx=20, pady=10)

        # Datos para las tarjetas
        tarjetas = [
            ("👥", "Clientes", str(stats.get("total_clientes", 0)), self.COLOR_VERDE),
            ("🔧", "Servicios", str(stats.get("total_servicios", 0)), "#a8dadc"),
            ("📋", "Reservas", str(stats.get("total_reservas", 0)), self.COLOR_ADVERTENCIA),
            ("💰", "Ingresos", f"${stats.get('ingresos_totales', 0):,.0f}", self.COLOR_EXITO),
        ]

        for icono, titulo, valor, color in tarjetas:
            # Cada tarjeta es un frame con icono, valor y título
            card = tk.Frame(frame_cards, bg=self.COLOR_SECUNDARIO, relief="flat", bd=1)
            card.pack(side="left", expand=True, fill="both", padx=5, pady=5)

            tk.Label(card, text=icono, font=("Segoe UI", 24), bg=self.COLOR_SECUNDARIO, fg=color).pack(pady=(15, 5))
            tk.Label(card, text=valor, font=("Segoe UI", 22, "bold"), bg=self.COLOR_SECUNDARIO, fg=color).pack()
            tk.Label(card, text=titulo, font=("Segoe UI", 10), bg=self.COLOR_SECUNDARIO, fg=self.COLOR_TEXTO).pack(pady=(2, 15))

        # ── RESUMEN DE RESERVAS ──
        frame_resumen = tk.Frame(self.frame_contenido, bg=self.COLOR_SECUNDARIO)
        frame_resumen.pack(fill="x", padx=20, pady=10)

        tk.Label(
            frame_resumen,
            text="📊 Estado de Reservas",
            font=("Segoe UI", 13, "bold"),
            bg=self.COLOR_SECUNDARIO,
            fg=self.COLOR_TEXTO
        ).pack(anchor="w", padx=15, pady=(15, 5))

        # Mostramos las últimas 5 reservas
        reservas = self.sistema.reservas[-5:]  # Tomamos las últimas 5
        if reservas:
            for reserva in reversed(reservas):  # Mostramos de más reciente a más antigua
                color_estado = {
                    Reserva.ESTADO_CONFIRMADA: self.COLOR_EXITO,
                    Reserva.ESTADO_CANCELADA: self.COLOR_ERROR,
                    Reserva.ESTADO_PENDIENTE: self.COLOR_ADVERTENCIA,
                    Reserva.ESTADO_COMPLETADA: self.COLOR_VERDE
                }.get(reserva.estado, self.COLOR_TEXTO)

                # Frame por cada reserva
                frame_r = tk.Frame(frame_resumen, bg=self.COLOR_ACENTO)
                frame_r.pack(fill="x", padx=15, pady=2)

                texto_reserva = (f"  #{reserva.id} | {reserva.cliente.nombre} → "
                                f"{reserva.servicio.nombre} | ${reserva.costo:,.0f}")
                tk.Label(frame_r, text=texto_reserva, font=("Segoe UI", 10),
                         bg=self.COLOR_ACENTO, fg=self.COLOR_TEXTO, anchor="w").pack(side="left", fill="x", expand=True, pady=5, padx=5)

                tk.Label(frame_r, text=f"[{reserva.estado}]", font=("Segoe UI", 10, "bold"),
                         bg=self.COLOR_ACENTO, fg=color_estado).pack(side="right", padx=10)
        else:
            tk.Label(frame_resumen, text="No hay reservas registradas",
                     font=("Segoe UI", 10), bg=self.COLOR_SECUNDARIO, fg=self.COLOR_TEXTO).pack(pady=10)

    def _mostrar_clientes(self):
        """
        Muestra la sección de gestión de clientes.
        Incluye formulario de registro y lista de clientes.
        """
        self._limpiar_contenido()
        self._crear_titulo_seccion("👥 Gestión de Clientes", f"Total: {len(self.sistema.clientes)} clientes")

        # ── FORMULARIO DE REGISTRO ──
        frame_form = tk.LabelFrame(
            self.frame_contenido,
            text=" ➕ Registrar Nuevo Cliente ",
            font=("Segoe UI", 11, "bold"),
            bg=self.COLOR_SECUNDARIO,
            fg=self.COLOR_VERDE,
            bd=2
        )
        frame_form.pack(fill="x", padx=20, pady=10)

        # Variables de Tkinter para los campos del formulario
        # StringVar permite vincular el valor del campo con una variable Python
        var_nombre = tk.StringVar()
        var_email = tk.StringVar()
        var_tel = tk.StringVar()
        var_empresa = tk.StringVar()

        # Creamos los campos del formulario con sus etiquetas
        campos = [
            ("Nombre completo *", var_nombre, 0),
            ("Email *", var_email, 1),
            ("Teléfono *", var_tel, 2),
            ("Empresa", var_empresa, 3),
        ]

        for etiqueta, variable, col in campos:
            # Organizamos en dos columnas usando grid
            tk.Label(frame_form, text=etiqueta, font=("Segoe UI", 10),
                     bg=self.COLOR_SECUNDARIO, fg=self.COLOR_TEXTO).grid(
                row=col // 2, column=(col % 2) * 2, padx=10, pady=8, sticky="e"
            )
            entry = tk.Entry(frame_form, textvariable=variable, font=("Segoe UI", 10),
                            bg=self.COLOR_ACENTO, fg=self.COLOR_BLANCO,
                            insertbackground=self.COLOR_BLANCO, width=30, relief="flat")
            entry.grid(row=col // 2, column=(col % 2) * 2 + 1, padx=10, pady=8, sticky="w")

        def registrar_cliente():
            """
            Función interna que se llama al presionar el botón de registro.
            Captura los valores del formulario y llama al sistema.
            """
            try:
                # Obtenemos los valores del formulario
                nombre = var_nombre.get().strip()
                email = var_email.get().strip()
                tel = var_tel.get().strip()
                empresa = var_empresa.get().strip()

                # Validación básica antes de enviar al sistema
                if not nombre or not email or not tel:
                    messagebox.showwarning("Campos requeridos",
                                          "Los campos marcados con * son obligatorios")
                    return

                # Llamamos al sistema para registrar
                cliente = self.sistema.registrar_cliente(nombre, email, tel, empresa)

                # Limpiamos el formulario después de registrar
                var_nombre.set("")
                var_email.set("")
                var_tel.set("")
                var_empresa.set("")

                # Mostramos mensaje de éxito
                messagebox.showinfo("✅ Cliente Registrado",
                                   f"Cliente '{cliente.nombre}' registrado con ID #{cliente.id}")

                # Actualizamos la lista
                actualizar_lista()

            except ClienteInvalidoError as e:
                messagebox.showerror("❌ Error de Validación", str(e))
            except SoftwareFJError as e:
                messagebox.showerror("❌ Error del Sistema", str(e))

        # Botón de registro
        tk.Button(
            frame_form,
            text="✅ Registrar Cliente",
            command=registrar_cliente,
            font=("Segoe UI", 11, "bold"),
            bg=self.COLOR_VERDE,
            fg=self.COLOR_PRIMARIO,
            activebackground=self.COLOR_EXITO,
            relief="flat",
            cursor="hand2",
            padx=20, pady=8
        ).grid(row=2, column=0, columnspan=4, pady=15)

        # ── LISTA DE CLIENTES ──
        frame_lista = tk.LabelFrame(
            self.frame_contenido,
            text=" 📋 Clientes Registrados ",
            font=("Segoe UI", 11, "bold"),
            bg=self.COLOR_SECUNDARIO,
            fg=self.COLOR_VERDE,
            bd=2
        )
        frame_lista.pack(fill="both", expand=True, padx=20, pady=10)

        # Tabla con columnas
        columnas = ("ID", "Nombre", "Email", "Teléfono", "Empresa", "Reservas", "Descuento")
        tabla = ttk.Treeview(frame_lista, columns=columnas, show="headings", height=8)

        # Configuramos cada columna
        anchos = [50, 180, 200, 130, 150, 80, 100]
        for col, ancho in zip(columnas, anchos):
            tabla.heading(col, text=col)                    # Encabezado
            tabla.column(col, width=ancho, anchor="center")  # Alineación y ancho

        # Scrollbar vertical para la tabla
        scrollbar = ttk.Scrollbar(frame_lista, orient="vertical", command=tabla.yview)
        tabla.configure(yscrollcommand=scrollbar.set)

        tabla.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def actualizar_lista():
            """Actualiza la tabla con los clientes actuales del sistema"""
            # Limpiamos todos los registros actuales de la tabla
            for item in tabla.get_children():
                tabla.delete(item)

            # Insertamos cada cliente
            for cliente in self.sistema.clientes:
                descuento = f"{cliente.descuento_fidelidad*100:.0f}%" if cliente.descuento_fidelidad > 0 else "—"
                tabla.insert("", "end", values=(
                    f"#{cliente.id}",
                    cliente.nombre,
                    cliente.email,
                    cliente.telefono,
                    cliente.empresa or "—",
                    cliente.total_reservas,
                    descuento
                ))

        actualizar_lista()  # Cargamos los clientes al mostrar la sección

    def _mostrar_servicios(self):
        """
        Muestra la sección de gestión de servicios.
        Incluye catálogo de servicios con sus detalles.
        """
        self._limpiar_contenido()
        self._crear_titulo_seccion("🔧 Catálogo de Servicios",
                                   f"Total: {len(self.sistema.servicios)} servicios disponibles")

        # ── FILTROS ──
        frame_filtros = tk.Frame(self.frame_contenido, bg=self.COLOR_SECUNDARIO)
        frame_filtros.pack(fill="x", padx=20, pady=5)

        tk.Label(frame_filtros, text="Filtrar por tipo:", font=("Segoe UI", 10),
                 bg=self.COLOR_SECUNDARIO, fg=self.COLOR_TEXTO).pack(side="left", padx=10, pady=5)

        # Variable para el filtro seleccionado
        var_filtro = tk.StringVar(value="Todos")

        # Botones de filtro para cada tipo de servicio
        for texto in ["Todos", "Sala", "Equipo", "Asesoría"]:
            tk.Radiobutton(
                frame_filtros,
                text=texto,
                variable=var_filtro,
                value=texto,
                command=lambda: actualizar_servicios(),  # Se llama al cambiar filtro
                font=("Segoe UI", 10),
                bg=self.COLOR_SECUNDARIO,
                fg=self.COLOR_TEXTO,
                selectcolor=self.COLOR_ACENTO,
                activebackground=self.COLOR_SECUNDARIO
            ).pack(side="left", padx=5)

        # LISTA DE SERVICIOS
        frame_lista = tk.Frame(self.frame_contenido, bg=self.COLOR_PRIMARIO)
        frame_lista.pack(fill="both", expand=True, padx=20, pady=10)

        # Usamos un canvas con scrollbar para poder hacer scroll en la lista
        canvas = tk.Canvas(frame_lista, bg=self.COLOR_PRIMARIO, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame_lista, orient="vertical", command=canvas.yview)
        frame_scroll = tk.Frame(canvas, bg=self.COLOR_PRIMARIO)

        # Configuramos el scroll
        frame_scroll.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame_scroll, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def actualizar_servicios():
            """Actualiza la lista de servicios según el filtro"""
            # Limpiamos el frame de scroll
            for widget in frame_scroll.winfo_children():
                widget.destroy()

            filtro = var_filtro.get()

            # Filtramos los servicios
            servicios_mostrar = []
            for s in self.sistema.servicios:
                if filtro == "Todos":
                    servicios_mostrar.append(s)
                elif filtro == "Sala" and isinstance(s, ReservaSala):
                    servicios_mostrar.append(s)
                elif filtro == "Equipo" and isinstance(s, AlquilerEquipo):
                    servicios_mostrar.append(s)
                elif filtro == "Asesoría" and isinstance(s, AsesoriaEspecializada):
                    servicios_mostrar.append(s)

            # Mostramos cada servicio como una tarjeta
            for servicio in servicios_mostrar:
                # Determinamos el color e ícono según el tipo
                if isinstance(servicio, ReservaSala):
                    color_tipo = "#a8dadc"
                    icono_tipo = "🏢"
                elif isinstance(servicio, AlquilerEquipo):
                    color_tipo = self.COLOR_ADVERTENCIA
                    icono_tipo = "💻"
                else:
                    color_tipo = self.COLOR_EXITO
                    icono_tipo = "🎓"

                # Creamos la tarjeta del servicio
                card = tk.Frame(frame_scroll, bg=self.COLOR_SECUNDARIO, relief="flat", bd=1)
                card.pack(fill="x", padx=5, pady=5)

                # Encabezado de la tarjeta con tipo e ID
                frame_card_header = tk.Frame(card, bg=self.COLOR_ACENTO)
                frame_card_header.pack(fill="x")

                tk.Label(frame_card_header, text=f"{icono_tipo} {servicio.obtener_tipo()}",
                         font=("Segoe UI", 9, "bold"), bg=self.COLOR_ACENTO,
                         fg=color_tipo).pack(side="left", padx=10, pady=5)

                tk.Label(frame_card_header, text=f"ID #{servicio.id}",
                         font=("Segoe UI", 9), bg=self.COLOR_ACENTO,
                         fg=self.COLOR_TEXTO).pack(side="right", padx=10)

                # Descripción del servicio (usamos el método polimórfico describir())
                descripcion = servicio.describir()
                tk.Label(card, text=descripcion, font=("Segoe UI", 10),
                         bg=self.COLOR_SECUNDARIO, fg=self.COLOR_TEXTO,
                         justify="left", anchor="w").pack(fill="x", padx=15, pady=10)

        actualizar_servicios()  # Cargamos los servicios al mostrar la sección

    def _mostrar_reservas(self):
        """
        Muestra la sección de gestión de reservas.
        Incluye formulario para crear reservas y tabla con el estado actual.
        """
        self._limpiar_contenido()
        self._crear_titulo_seccion("📋 Gestión de Reservas",
                                   f"Total: {len(self.sistema.reservas)} reservas")

        # FORMULARIO DE NUEVA RESERVA
        frame_form = tk.LabelFrame(
            self.frame_contenido,
            text=" ➕ Crear Nueva Reserva ",
            font=("Segoe UI", 11, "bold"),
            bg=self.COLOR_SECUNDARIO,
            fg=self.COLOR_VERDE,
            bd=2
        )
        frame_form.pack(fill="x", padx=20, pady=10)

        # Variables del formulario
        var_cliente_id = tk.StringVar()
        var_servicio_id = tk.StringVar()
        var_duracion = tk.StringVar()

        # Fila 1: Cliente
        tk.Label(frame_form, text="ID del Cliente:", font=("Segoe UI", 10),
                 bg=self.COLOR_SECUNDARIO, fg=self.COLOR_TEXTO).grid(row=0, column=0, padx=10, pady=8, sticky="e")

        # Combo con los clientes disponibles (ID - Nombre)
        clientes_opciones = [f"{c.id} - {c.nombre}" for c in self.sistema.clientes]
        combo_clientes = ttk.Combobox(frame_form, textvariable=var_cliente_id,
                                      values=clientes_opciones, width=30, state="readonly")
        combo_clientes.grid(row=0, column=1, padx=10, pady=8)

        # Fila 2: Servicio 
        tk.Label(frame_form, text="ID del Servicio:", font=("Segoe UI", 10),
                 bg=self.COLOR_SECUNDARIO, fg=self.COLOR_TEXTO).grid(row=0, column=2, padx=10, pady=8, sticky="e")

        servicios_opciones = [f"{s.id} - {s.nombre}" for s in self.sistema.servicios]
        combo_servicios = ttk.Combobox(frame_form, textvariable=var_servicio_id,
                                       values=servicios_opciones, width=30, state="readonly")
        combo_servicios.grid(row=0, column=3, padx=10, pady=8)

        # Fila 3: Duración
        tk.Label(frame_form, text="Duración:", font=("Segoe UI", 10),
                 bg=self.COLOR_SECUNDARIO, fg=self.COLOR_TEXTO).grid(row=1, column=0, padx=10, pady=8, sticky="e")

        entry_duracion = tk.Entry(frame_form, textvariable=var_duracion, font=("Segoe UI", 10),
                                  bg=self.COLOR_ACENTO, fg=self.COLOR_BLANCO,
                                  insertbackground=self.COLOR_BLANCO, width=15, relief="flat")
        entry_duracion.grid(row=1, column=1, padx=10, pady=8, sticky="w")

        tk.Label(frame_form, text="(horas / días / sesiones según el servicio)",
                 font=("Segoe UI", 9), bg=self.COLOR_SECUNDARIO,
                 fg="#888888").grid(row=1, column=2, columnspan=2, padx=5, sticky="w")

        # Etiqueta para mostrar el costo estimado
        lbl_costo = tk.Label(frame_form, text="💰 Costo estimado: seleccione cliente y servicio",
                             font=("Segoe UI", 10), bg=self.COLOR_SECUNDARIO, fg=self.COLOR_ADVERTENCIA)
        lbl_costo.grid(row=2, column=0, columnspan=4, pady=5)

        def calcular_costo_preview(*args):
            """
            Calcula y muestra una vista previa del costo antes de confirmar.
            Se llama automáticamente cuando cambia algún campo.
            """
            try:
                # Obtenemos los valores seleccionados
                sel_cliente = var_cliente_id.get()
                sel_servicio = var_servicio_id.get()
                dur_str = var_duracion.get()

                # Verificamos que todos los campos tengan valor
                if not sel_cliente or not sel_servicio or not dur_str:
                    return

                # Extraemos los IDs del formato "ID - Nombre"
                cliente_id = int(sel_cliente.split(" - ")[0])
                servicio_id = int(sel_servicio.split(" - ")[0])
                duracion = float(dur_str)

                # Buscamos el servicio para calcular el costo
                servicio = next((s for s in self.sistema.servicios if s.id == servicio_id), None)
                cliente = next((c for c in self.sistema.clientes if c.id == cliente_id), None)

                if servicio and cliente:
                    # Calculamos el costo con descuento si tiene
                    resultado = servicio.calcular_costo_con_descuento(duracion, cliente.descuento_fidelidad)
                    costo = resultado["precio_final"]
                    descuento = resultado["porcentaje_descuento"]

                    if descuento > 0:
                        lbl_costo.config(
                            text=f"💰 Costo: ${resultado['precio_original']:,.0f} → "
                                 f"${costo:,.0f} (con {descuento:.0f}% descuento fidelidad)",
                            fg=self.COLOR_EXITO
                        )
                    else:
                        lbl_costo.config(text=f"💰 Costo estimado: ${costo:,.0f}", fg=self.COLOR_ADVERTENCIA)

            except (ValueError, IndexError, ServicioInvalidoError, CalculoError):
                pass  # Si hay error en el preview, simplemente no mostramos nada

        # Vinculamos la función al cambio de los campos
        var_cliente_id.trace("w", calcular_costo_preview)
        var_servicio_id.trace("w", calcular_costo_preview)
        var_duracion.trace("w", calcular_costo_preview)

        def crear_reserva():
            """Función para crear la reserva al presionar el botón"""
            try:
                # Validamos que los campos tengan valor
                if not var_cliente_id.get() or not var_servicio_id.get() or not var_duracion.get():
                    messagebox.showwarning("Campos requeridos", "Complete todos los campos")
                    return

                # Extraemos los IDs
                cliente_id = int(var_cliente_id.get().split(" - ")[0])
                servicio_id = int(var_servicio_id.get().split(" - ")[0])

                # Convertimos la duración a número
                try:
                    duracion = float(var_duracion.get())
                except ValueError:
                    messagebox.showerror("Error", "La duración debe ser un número válido")
                    return

                # Creamos la reserva
                reserva = self.sistema.crear_reserva(cliente_id, servicio_id, duracion)

                messagebox.showinfo("✅ Reserva Creada",
                                   f"Reserva #{reserva.id} creada exitosamente\n"
                                   f"Costo total: ${reserva.costo:,.0f}")

                # Limpiamos el formulario
                var_cliente_id.set("")
                var_servicio_id.set("")
                var_duracion.set("")
                lbl_costo.config(text="💰 Costo estimado: seleccione cliente y servicio",
                                fg=self.COLOR_ADVERTENCIA)

                # Actualizamos la tabla
                actualizar_tabla()

            except ReservaError as e:
                messagebox.showerror("❌ Error en Reserva", str(e))
            except DisponibilidadError as e:
                messagebox.showerror("❌ Sin Disponibilidad", str(e))
            except ServicioInvalidoError as e:
                messagebox.showerror("❌ Servicio Inválido", str(e))
            except SoftwareFJError as e:
                messagebox.showerror("❌ Error del Sistema", str(e))

        # Botón crear reserva
        tk.Button(
            frame_form,
            text="📋 Crear Reserva",
            command=crear_reserva,
            font=("Segoe UI", 11, "bold"),
            bg=self.COLOR_VERDE,
            fg=self.COLOR_PRIMARIO,
            activebackground=self.COLOR_EXITO,
            relief="flat",
            cursor="hand2",
            padx=20, pady=8
        ).grid(row=3, column=0, columnspan=4, pady=10)

        # TABLA DE RESERVAS
        frame_tabla = tk.LabelFrame(
            self.frame_contenido,
            text=" 📊 Historial de Reservas ",
            font=("Segoe UI", 11, "bold"),
            bg=self.COLOR_SECUNDARIO,
            fg=self.COLOR_VERDE,
            bd=2
        )
        frame_tabla.pack(fill="both", expand=True, padx=20, pady=10)

        # Tabla con columnas
        columnas = ("ID", "Cliente", "Servicio", "Tipo", "Duración", "Costo", "Estado", "Fecha")
        tabla = ttk.Treeview(frame_tabla, columns=columnas, show="headings", height=8)

        anchos = [50, 150, 180, 130, 80, 100, 110, 110]
        for col, ancho in zip(columnas, anchos):
            tabla.heading(col, text=col)
            tabla.column(col, width=ancho, anchor="center")

        # Scrollbar
        sb = ttk.Scrollbar(frame_tabla, orient="vertical", command=tabla.yview)
        tabla.configure(yscrollcommand=sb.set)
        tabla.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Botones de acción
        frame_botones = tk.Frame(frame_tabla, bg=self.COLOR_SECUNDARIO)
        frame_botones.pack(fill="x", pady=5)

        def cancelar_seleccionada():
            """Cancela la reserva seleccionada en la tabla"""
            seleccion = tabla.selection()  # Obtenemos la fila seleccionada
            if not seleccion:
                messagebox.showwarning("Sin selección", "Seleccione una reserva para cancelar")
                return

            # Obtenemos el ID de la reserva seleccionada
            item = tabla.item(seleccion[0])
            reserva_id_str = item["values"][0]
            reserva_id = int(str(reserva_id_str).replace("#", ""))

            try:
                reserva = self.sistema.cancelar_reserva(reserva_id, "Cancelada desde la interfaz")
                messagebox.showinfo("✅ Cancelada", f"Reserva #{reserva_id} cancelada correctamente")
                actualizar_tabla()
            except ReservaError as e:
                messagebox.showerror("❌ Error", str(e))

        tk.Button(
            frame_botones,
            text="❌ Cancelar Seleccionada",
            command=cancelar_seleccionada,
            font=("Segoe UI", 10),
            bg=self.COLOR_ERROR,
            fg=self.COLOR_BLANCO,
            relief="flat",
            cursor="hand2",
            padx=15, pady=5
        ).pack(side="left", padx=10, pady=5)

        def actualizar_tabla():
            """Actualiza la tabla con las reservas actuales"""
            for item in tabla.get_children():
                tabla.delete(item)

            for reserva in reversed(self.sistema.reservas):  # Más recientes primero
                # Coloreamos según el estado
                tag = reserva.estado.lower()

                tabla.insert("", "end", tags=(tag,), values=(
                    f"#{reserva.id}",
                    reserva.cliente.nombre,
                    reserva.servicio.nombre,
                    reserva.servicio.obtener_tipo(),
                    reserva.duracion,
                    f"${reserva.costo:,.0f}",
                    reserva.estado,
                    str(reserva.fecha_servicio)
                ))

            # Configuramos colores por estado
            tabla.tag_configure("confirmada", foreground="#2ec4b6")
            tabla.tag_configure("cancelada", foreground="#e63946")
            tabla.tag_configure("pendiente", foreground="#ffd166")
            tabla.tag_configure("completada", foreground="#a8dadc")

        actualizar_tabla()

    def _mostrar_estadisticas(self):
        """
        Muestra estadísticas detalladas del sistema.
        """
        self._limpiar_contenido()
        self._crear_titulo_seccion("📊 Estadísticas del Sistema", "Análisis general de operaciones")

        stats = self.sistema.obtener_estadisticas()

        # ── PANEL DE ESTADÍSTICAS DETALLADAS ──
        frame_stats = tk.Frame(self.frame_contenido, bg=self.COLOR_PRIMARIO)
        frame_stats.pack(fill="both", expand=True, padx=20, pady=10)

        # Estadísticas en formato de texto detallado
        texto_stats = scrolledtext.ScrolledText(
            frame_stats,
            font=("Consolas", 11),              # Fuente monoespaciada para mejor lectura
            bg=self.COLOR_SECUNDARIO,
            fg=self.COLOR_TEXTO,
            insertbackground=self.COLOR_BLANCO,
            relief="flat",
            wrap="word"
        )
        texto_stats.pack(fill="both", expand=True)

        # Construimos el reporte
        reporte = []
        reporte.append("=" * 60)
        reporte.append("    SOFTWARE FJ - REPORTE DE ESTADÍSTICAS")
        reporte.append(f"    Generado: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        reporte.append("=" * 60)
        reporte.append("")
        reporte.append("📋 RESUMEN GENERAL:")
        reporte.append(f"   • Clientes registrados:    {stats.get('total_clientes', 0):>10}")
        reporte.append(f"   • Servicios disponibles:   {stats.get('total_servicios', 0):>10}")
        reporte.append(f"   • Total reservas:          {stats.get('total_reservas', 0):>10}")
        reporte.append("")
        reporte.append("📊 ESTADO DE RESERVAS:")
        reporte.append(f"   • Confirmadas:             {stats.get('reservas_confirmadas', 0):>10}")
        reporte.append(f"   • Canceladas:              {stats.get('reservas_canceladas', 0):>10}")
        reporte.append(f"   • Completadas:             {stats.get('reservas_completadas', 0):>10}")
        reporte.append("")
        reporte.append("💰 INFORMACIÓN FINANCIERA:")
        reporte.append(f"   • Ingresos totales:  ${stats.get('ingresos_totales', 0):>16,.0f} COP")
        reporte.append("")

        # Desglose por tipo de servicio
        reporte.append("🔧 SERVICIOS POR TIPO:")
        for servicio in self.sistema.servicios:
            reporte.append(f"   [{servicio.obtener_tipo()[:20]:<20}] {servicio.nombre}")

        reporte.append("")
        reporte.append("👥 CLIENTES CON MÁS RESERVAS:")
        clientes_ordenados = sorted(self.sistema.clientes,
                                    key=lambda c: c.total_reservas, reverse=True)
        for i, cliente in enumerate(clientes_ordenados[:5], 1):
            desc = f" (descuento {cliente.descuento_fidelidad*100:.0f}%)" if cliente.descuento_fidelidad > 0 else ""
            reporte.append(f"   {i}. {cliente.nombre:<25} - {cliente.total_reservas} reservas{desc}")

        reporte.append("")
        reporte.append("=" * 60)
        reporte.append("    FIN DEL REPORTE")
        reporte.append("=" * 60)

        # Mostramos el reporte en el widget de texto
        texto_stats.insert("1.0", "\n".join(reporte))
        texto_stats.config(state="disabled")  # Hacemos el texto de solo lectura

    def _mostrar_logs(self):
        """
        Muestra los logs del sistema en tiempo real.
        """
        self._limpiar_contenido()
        self._crear_titulo_seccion("📝 Registro de Eventos (Logs)",
                                   "Historial de operaciones y errores del sistema")

        # ── ÁREA DE LOGS ──
        frame_logs = tk.Frame(self.frame_contenido, bg=self.COLOR_PRIMARIO)
        frame_logs.pack(fill="both", expand=True, padx=20, pady=10)

        # Widget de texto con scroll para mostrar los logs
        texto_logs = scrolledtext.ScrolledText(
            frame_logs,
            font=("Consolas", 10),           # Fuente monoespaciada para logs
            bg="#0a0a1a",                    # Fondo muy oscuro (estilo terminal)
            fg="#00ff41",                    # Verde brillante (estilo Matrix)
            insertbackground="#00ff41",
            relief="flat",
            wrap="word"
        )
        texto_logs.pack(fill="both", expand=True)

        # Obtenemos los logs del sistema
        logs = SistemaLogs().obtener_logs(100)  # Últimos 100 logs

        # Mostramos cada log con colores según el nivel
        for log in logs:
            # Determinamos el color según el nivel del log
            if "[ERROR]" in log:
                color = "#e63946"          # Rojo para errores
                texto_logs.insert("end", log + "\n", "error")
            elif "[ADVERTENCIA]" in log:
                color = "#ffd166"          # Amarillo para advertencias
                texto_logs.insert("end", log + "\n", "advertencia")
            elif "[INFO]" in log:
                color = "#2ec4b6"          # Verde azulado para información
                texto_logs.insert("end", log + "\n", "info")
            else:
                color = "#888888"          # Gris para debug y otros
                texto_logs.insert("end", log + "\n", "debug")

        # Configuramos los colores de cada tag
        texto_logs.tag_configure("error", foreground="#e63946")
        texto_logs.tag_configure("advertencia", foreground="#ffd166")
        texto_logs.tag_configure("info", foreground="#2ec4b6")
        texto_logs.tag_configure("debug", foreground="#888888")

        # Hacemos scroll hasta el final automáticamente
        texto_logs.see("end")
        texto_logs.config(state="disabled")  # Solo lectura

        # Botón para actualizar los logs
        tk.Button(
            self.frame_contenido,
            text="🔄 Actualizar Logs",
            command=self._mostrar_logs,   # Recargamos la vista de logs
            font=("Segoe UI", 10),
            bg=self.COLOR_ACENTO,
            fg=self.COLOR_TEXTO,
            activebackground=self.COLOR_VERDE,
            relief="flat",
            cursor="hand2",
            padx=15, pady=5
        ).pack(pady=5)

# Configuré el punto de inicio del programa para ejecutar correctamente el sistema.

def main():
    """
    Función principal que inicia la aplicación.
    Es el punto de entrada del programa.
    """
    try:
        # Creamos la ventana principal de Tkinter
        root = tk.Tk()

        # Aplicamos el estilo moderno de Tkinter (tema clam)
        estilo = ttk.Style()
        estilo.theme_use("clam")                    # Tema base

        # Personalizamos el estilo de la tabla (Treeview)
        estilo.configure("Treeview",
                         background="#16213e",      # Fondo de filas
                         foreground="#e0e0e0",      # Color del texto
                         rowheight=28,              # Altura de cada fila
                         fieldbackground="#16213e"  # Fondo del área de datos
                         )
        # Estilo del encabezado de la tabla
        estilo.configure("Treeview.Heading",
                         background="#0f3460",
                         foreground="#00b4d8",
                         font=("Segoe UI", 10, "bold")
                         )
        # Estilo al seleccionar una fila
        estilo.map("Treeview",
                   background=[("selected", "#0f3460")],
                   foreground=[("selected", "#00b4d8")]
                   )

        # Creamos la aplicación pasando la ventana root
        app = AplicacionFJ(root)

        # Iniciamos el bucle principal de la GUI
        # Este bucle mantiene la ventana abierta y responde a eventos (clics, teclado, etc.)
        root.mainloop()

    except Exception as e:
        # Si hay un error fatal al iniciar, lo registramos y mostramos un mensaje
        print(f"Error fatal al iniciar la aplicación: {e}")
        SistemaLogs().registrar("CRITICO", "Error fatal al iniciar la aplicación", e)

# Esta condición verifica si el script se está ejecutando directamente
# (no importado como módulo). Si es así, llamamos a main().
if __name__ == "__main__":
    main()