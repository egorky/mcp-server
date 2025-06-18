document.addEventListener('DOMContentLoaded', function() {
    const toolSelector = document.getElementById('tool-selector');
    const toolConfigContainer = document.getElementById('tool-config-container');
    const selectedToolNameDisplay = document.getElementById('selected-tool-name');
    const selectedToolDescriptionDisplay = document.getElementById('selected-tool-description');
    const toolParamsFormFields = document.getElementById('tool-params-form-fields');
    const toolExecutionForm = document.getElementById('tool-execution-form');
    const toolOutputContainer = document.getElementById('tool-output-container');
    const toolOutputContent = document.getElementById('tool-output-content');

    let allToolsData = {}; // Store all tool details

    // Fetch tools and populate selector (if on dashboard)
    if (toolSelector) {
        fetch('/tools')
            .then(response => response.json())
            .then(tools => {
                allToolsData = tools; // Save for later
                for (const toolName in tools) {
                    const option = document.createElement('option');
                    option.value = toolName;
                    option.textContent = tools[toolName].name || toolName; // Use provided name or key
                    toolSelector.appendChild(option);
                }
            })
            .catch(error => console.error('Error fetching tools:', error));

        toolSelector.addEventListener('change', function() {
            const selectedToolName = this.value;
            toolConfigContainer.style.display = 'none';
            toolOutputContainer.style.display = 'none';
            toolParamsFormFields.innerHTML = ''; // Clear previous params

            if (selectedToolName && allToolsData[selectedToolName]) {
                const tool = allToolsData[selectedToolName];
                selectedToolNameDisplay.textContent = tool.name || selectedToolName;
                selectedToolDescriptionDisplay.textContent = tool.description;

                const configSpec = tool.config_spec;
                for (const paramName in configSpec) {
                    const spec = configSpec[paramName];
                    const paramDiv = document.createElement('div');

                    const label = document.createElement('label');
                    label.setAttribute('for', 'param-' + paramName);
                    label.textContent = spec.description || paramName;
                    if (spec.required) {
                        label.textContent += ' (required)';
                    }
                    paramDiv.appendChild(label);

                    let input;
                    if (spec.type === 'boolean') {
                        input = document.createElement('select');
                        input.id = 'param-' + paramName;
                        input.name = paramName;
                        const trueOpt = document.createElement('option');
                        trueOpt.value = 'true';
                        trueOpt.textContent = 'True';
                        input.appendChild(trueOpt);
                        const falseOpt = document.createElement('option');
                        falseOpt.value = 'false';
                        falseOpt.textContent = 'False';
                        input.appendChild(falseOpt);
                        if (spec.default !== undefined) {
                            input.value = spec.default.toString();
                        }
                    } else if (spec.type === 'integer') {
                        input = document.createElement('input');
                        input.type = 'number';
                        input.id = 'param-' + paramName;
                        input.name = paramName;
                        if (spec.default !== undefined) {
                            input.value = spec.default;
                        }
                    } else { // Default to string/text
                        input = document.createElement('input');
                        input.type = 'text';
                        input.id = 'param-' + paramName;
                        input.name = paramName;
                        if (spec.default !== undefined) {
                            input.value = spec.default;
                        }
                    }
                     if (spec.required) {
                        input.required = true;
                    }
                    paramDiv.appendChild(input);
                    toolParamsFormFields.appendChild(paramDiv);
                }
                toolConfigContainer.style.display = 'block';
            }
        });

        toolExecutionForm.addEventListener('submit', function(event) {
            event.preventDefault();
            const selectedToolName = toolSelector.value;
            if (!selectedToolName) {
                alert('Please select a tool first.');
                return;
            }

            const formData = new FormData(this);
            const params = {};
            const configSpec = allToolsData[selectedToolName].config_spec;

            for (let [key, value] of formData.entries()) {
                // Convert to correct type based on config_spec
                if (configSpec[key]) {
                    if (configSpec[key].type === 'integer') {
                        params[key] = value === '' && !configSpec[key].required ? null : parseInt(value, 10);
                    } else if (configSpec[key].type === 'boolean') {
                        params[key] = value === 'true';
                    } else {
                        params[key] = value;
                    }
                     // Handle empty non-required fields - set to null or undefined if appropriate
                    if (value === '' && !configSpec[key].required) {
                        // For some tools, an empty string is different from not providing the param.
                        // Let server-side validation handle this, or set to undefined/null if your tool expects it.
                        // For now, sending empty string if not required and empty.
                        // Or, if default exists and value is empty, it should have been set by default.
                        // This logic might need refinement based on how tools handle missing optional params.
                        if(configSpec[key].default === undefined) params[key] = null; // more explicit "not set"
                        else params[key] = value; // let it be empty string if that's what user provided
                    }

                } else {
                     params[key] = value; // Should not happen if form is built correctly
                }
            }
             // Ensure all required params are present, even if not in FormData (e.g. unchecked checkbox for boolean)
            for (const paramName in configSpec) {
                if (configSpec[paramName].required && !(paramName in params)) {
                    // This case is mostly for boolean false if not submitted.
                    if (configSpec[paramName].type === 'boolean') {
                         // HTML forms don't submit unchecked checkboxes.
                         // If it's required and not in params, it must be false (assuming checkbox).
                         // For select, it would be present.
                         // This is tricky. The current select for boolean always sends a value.
                    } else {
                        // This should be caught by form's `required` attribute, but as a fallback:
                        // alert(`Missing required parameter: ${paramName}`);
                        // return;
                    }
                }
                 // If a param is not in params (e.g. empty optional field) and has a default, it's fine.
                 // If it's not in params and has no default, and not required, it's also fine (becomes null or undefined).
                 if (!(paramName in params) && params[paramName] !== null && configSpec[paramName].default === undefined && !configSpec[paramName].required) {
                    params[paramName] = null; // Explicitly set to null if not provided, not required, and no default
                 }
            }


            toolOutputContainer.style.display = 'block';
            toolOutputContent.textContent = 'Executing...';

            fetch(`/tools/${selectedToolName}/execute`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(params),
            })
            .then(response => response.json())
            .then(result => {
                toolOutputContent.textContent = JSON.stringify(result, null, 2);
            })
            .catch(error => {
                console.error('Error executing tool:', error);
                toolOutputContent.textContent = 'Error: ' + error.message;
            });
        });
    }

    // Basic login page logic (if any needed beyond HTML form submission)
    // For now, login is a simple form post.
    const loginForm = document.querySelector('form[action="{{ url_for('login') }}"]'); // This template var won't work in static JS
    // So, no specific JS for login form for now unless we add IDs or classes.
});
