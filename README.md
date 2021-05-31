# Reporting-INGInious-plugin

This plugin allows to display histogram for data analysis of INGInious submissions

## Installing

``pip3 install git+https://github.com/UCL-INGI/INGInious-reporting-plugin``

## Ativating

In your `configuration.yaml` file, add the following plugin entry:
```
plugins:
  - plugin_module: "INGInious-reporting"
        networkname: "A network name"
        networkv4: "An IPv4 of the network to verify"
        networkv6: "An IPv6 of the network to verify"
  
```
