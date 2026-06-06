import re

with open("src/lib/components/SetupScreen.svelte", "r") as f:
    content = f.read()

# Remove imports for apiKey and apiKeyError
content = re.sub(r'\bapiKey,\s*', '', content)
content = re.sub(r'\bapiKeyError,\s*', '', content)

# Replace gemini with ollama
content = content.replace('gemini: true', 'ollama: true')
content = content.replace('gemini: false', 'ollama: false')
content = content.replace('gemini: null', 'ollama: null')
content = content.replace('c.gemini', 'c.ollama')
content = content.replace('gemini: "Gemini API"', 'ollama: "Ollama Server"')
content = content.replace('Internet connection and a valid Gemini API key are required for\\n              Mia to function.', 'A running Ollama server is required for Mia to function.')
content = content.replace('Internet connection and a valid Gemini API key are required for\n              Mia to function.', 'A running Ollama server is required for Mia to function.')
content = content.replace('Internet connection and a valid Gemini API key are required', 'A running Ollama server is required')
content = content.replace('A running Ollama server is required for\\n              Mia to function.', 'A running Ollama server is required for Mia to function.')

# Remove apiKey block
content = re.sub(r'let key = "";\n\s*function handleKeySubmit\(\) \{.*?\n\s*\}\n', '', content, flags=re.DOTALL)

# Change setupStep.set('api_key') to setupStep.set('checks') and remove goBackToApiKey
content = content.replace("setupStep.set('api_key');", "setupStep.set('checks');")
content = re.sub(r'function goBackToApiKey\(\) \{.*?\n\s*\}\n', '', content, flags=re.DOTALL)

# Remove the HTML block for api_key
content = re.sub(r'\{:else if \$setupStep === "api_key"\}[\s\S]*?\{:else if \$setupStep === "checks"\}', '{:else if $setupStep === "checks"}', content)

# Remove back buttons
content = re.sub(r'<button on:click=\{goBackToApiKey\} class="back-btn[^"]*">.*?<\/button>', '', content, flags=re.DOTALL)

# Fix config message handling: it goes to "checks" instead of "api_key"
content = content.replace('setupStep.set("api_key");', 'setupStep.set("checks");')

with open("src/lib/components/SetupScreen.svelte", "w") as f:
    f.write(content)
