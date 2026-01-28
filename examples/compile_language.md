# Compile a MAL Language


## Prerequisites:
- Install [maltoolbox](https://github.com/mal-lang/mal-toolbox)
- Create/download a MAL language in .mal file(s)

Note: You can also load .mal-files directly in the MAL-toolbox, but compiling the language with malc is still adviced since it has better error handling than the toolbox.

<!-- ## Option 1: Use the MAL Toolbox to compile the language

- Use `maltoolbox compile` to output a language specification that can be used in the mal-toolbox

Example compile coreLang:

```bash
# Download coreLang (you can do this without git as well)
git clone https://github.com/mal-lang/coreLang.git

# Move into the coreLang directory
cd coreLang

# Compile coreLang (we are in the coreLang root directory)
# This will output coreLang.json which is a language specification
maltoolbox compile src/main/mal/main.mal coreLang.json
``` -->

## Compile a MAL Language with malc

- Use [malc](https://github.com/mal-lang/malc/releases)
- Compile your language with malc: https://github.com/mal-lang/malc?tab=readme-ov-file#usage
- This will result in a .mar-archive of your language that can be used by the MAL toolbox.

Example compile coreLang on ubuntu machine:

```bash
# Download coreLang (you can do this without git as well)
git clone https://github.com/mal-lang/coreLang.git

# Move into the coreLang directory
cd coreLang

# Download malc (correct version for your OS can be found on https://github.com/mal-lang/malc/releases)
wget https://github.com/mal-lang/malc/releases/download/release%2F0.2.0/malc_0.2.0-1_amd64.deb

# Install malc
sudo dpkg -i malc_0.2.0-1_amd64.deb

# Compile coreLang (we are in the coreLang root directory)
# This will output org.mal-lang.coreLang-1.0.0.mar which,
# a '.mar'-archive containing the language.
malc src/main/mal/main.mal

```
