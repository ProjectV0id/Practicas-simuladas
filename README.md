
Desarrollado por: Kevin Andres Erazo Salazar

Mi sistema de gestión.
Se realizo es programa para demostrar cómo armar una aplicación robusta usando solo objetos y listas, sin tocar ninguna base de datos. Todo el control de datos y errores lo programé directamente en Python.

Lo que hice en el código:
Manejo de datos: Como no hay SQL, usé una clase abstracta Entidad para que cada cliente o servicio tenga su propio ID automático mediante un contador global. Así mantengo todo ordenado en memoria.

Filtros de entrada: Para que el sistema no se llene de basura, puse un Regex en la clase Cliente. Si el correo no tiene el formato correcto, el sistema frena el registro de una vez.

Lógica de cobro: Usé Polimorfismo para que el cálculo de precios sea automático. Mi código diferencia si es una Sala o un Equipo, aplicando cargos o seguros distintos según el objeto.

Cero cierres inesperados: Me enfoqué en que la app sea estable. En la línea 804 metí un bloque try/except/else/finally para que, aunque el usuario cometa un error, el sistema lo capture, lo guarde en el log y siga funcionando.

Historial técnico: Programé un Singleton (Línea 112) para los logs. Todo lo que pasa en el programa se escribe en el archivo sistema_reservas.log, así tengo un rastro real de cada operación.

Prueba de funcionamiento
Corrí una simulación de 10 operaciones mezclando datos buenos y malos. El sistema demostró que mis excepciones personalizadas funcionan: rechazan lo que está mal, pero mantienen la aplicación abierta y lista para seguir.