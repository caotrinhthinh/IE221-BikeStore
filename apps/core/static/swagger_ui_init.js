(function () {
    var Bundle = window.SwaggerUIBundle;
    var StandalonePreset = window.SwaggerUIStandalonePreset;

    if (!Bundle) {
        document.getElementById('swagger-ui').innerHTML =
            '<p style="padding:2rem;font-family:sans-serif;color:red">Error: SwaggerUIBundle not loaded.</p>';
        return;
    }

    var schemaUrl = document.getElementById('swagger-ui').dataset.schemaUrl || '/api/schema/?format=json';

    Bundle({
        url: schemaUrl,
        dom_id: '#swagger-ui',
        presets: [Bundle.presets.apis, StandalonePreset || Bundle.presets.apis],
        layout: StandalonePreset ? 'StandaloneLayout' : 'BaseLayout',
        deepLinking: true,
        persistAuthorization: true,
        displayOperationId: false,
    });
})();
