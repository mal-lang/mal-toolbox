# Configure MAL-toolbox

MAL-toolbox uses a config file that sets logging and visualizer settings.

To write your own config file, create a file called 'maltoolbox.yml' and place it in the directory from where you are running mal-toolbox. The content of the file should be this:

```yml
logging: 
  log_level: INFO
  log_file: "logs/log.txt"
  attackgraph_file: "logs/attackgraph.yml"
  model_file: "logs/model.yml"
  langspec_file: "logs/langspec_file.yml"
```

You can change log level, log file, and output file paths.
