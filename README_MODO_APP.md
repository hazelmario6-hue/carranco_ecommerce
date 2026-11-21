# Modo web y aplicación Carranco

El APK envía `CarrancoApp/3` en su User-Agent; `CarrancoApp/2` también funciona. Django decide la presentación en cada solicitud. El navegador normal, incluso en un teléfono, conserva el encabezado, el pie y el diseño web.

`?modo=app` es una vista previa **solo de esa solicitud**. No deja una cookie ni cambia las páginas siguientes. Las cookies de vista previa de versiones anteriores se eliminan automáticamente. `?modo=web` fuerza la vista web en esa solicitud.

Las cuentas de personal (`is_staff` activo) siempre usan la presentación web. Después de iniciar sesión entran a `/dashboard/`, conservando su sesión. Dentro del APK el dashboard web se abre en el mismo WebView; no se transfieren contraseñas ni cookies a un navegador externo. Los permisos se comprueban también en el servidor. Al cerrar sesión el APK vuelve al modo cliente.

La app utiliza alturas flexibles, `100dvh`, zonas seguras y espacio inferior medido según la barra de navegación. Oculta esa barra durante la apertura del teclado. El Android 1.2 activa el viewport adaptable; mantiene su pantalla local de inicio y sin conexión.

Los enlaces externos de la app usan navegación en la misma ventana para que `shouldOverrideUrlLoading` los envíe a Android. El sistema abre la app correspondiente o un navegador. En modo web se abren en otra pestaña con `noopener noreferrer`. No se ejecutan llamadas automáticas ni se envían mensajes al bot al abrir la página.

Para subir los cambios de Django, migrar promociones y generar el APK, consulta `GUIA_ACTUALIZACION.md`. Para las pruebas realizadas consulta `docs/VERIFICACION_2026-11-20.md`.
