#!/usr/bin/env python3
"""
Master Validation Script for mia_n_eve.
Runs all validation scripts and generates hardware-notes.md.
"""
import subprocess
import sys
import os

def run_script(script_name):
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    try:
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        return result.stdout, result.returncode == 0
    except Exception as e:
        return f"Error running {script_name}: {e}", False

def main():
    print("Running Eve Environment Validation...\n")
    
    scripts = [
        ("GPU", "validate_gpu.py"),
        ("Audio", "validate_audio.py"),
        ("STT", "validate_stt.py"),
        ("TTS", "validate_tts.py"),
        ("LLM", "validate_llm.py"),
    ]
    
    full_output = []
    summary_lines = []
    
    for name, script in scripts:
        print(f"Running {name} validation...")
        out, ok = run_script(script)
        status = "✅" if ok else "❌"
        summary_lines.append(f"| {name:<12} | {status} |")
        
        full_output.append(f"### {name} Validation\n```text\n{out.strip()}\n```\n")
        
    # Generate markdown content
    md_content = "# Eve Environment Hardware Notes\n\n"
    md_content += "## Summary\n\n"
    md_content += "| Component    | Status |\n"
    md_content += "|--------------|--------|\n"
    md_content += "\n".join(summary_lines)
    md_content += "\n\n## Detailed Logs\n\n"
    md_content += "\n".join(full_output)
    
    notes_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'hardware-notes.md'))
    
    with open(notes_path, 'w') as f:
        f.write(md_content)
        
    print(f"\nValidation complete. Results saved to {notes_path}")

if __name__ == "__main__":
    main()
