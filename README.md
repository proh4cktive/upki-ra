![ProHacktive](https://prohacktive.io/public/images/logo-prohacktive-grey-dark.svg "uPKI from ProHacktive.io")

# µPKI-RA
***NOT READY FOR PRODUCTION USE***
This project has only been tested on Debian 9 Strech with Python3.6.
Due to python usage it *SHOULD* works on many other configurations, but it has NOT been tested.

## 1. About
µPki [maɪkroʊ ˈpiː-ˈkeɪ-ˈaɪ] is a small PKI in python that should let you make basic tasks without effort.
It works in combination with:
> - [µPKI-CA](https://github.com/proh4cktive/upki)
> - [µPKI-WEB](https://github.com/proh4cktive/upki-web)
> - [µPKI-CLI](https://github.com/proh4cktive/upki-cli)

µPki-RA is the Registration AUthority service that interact with the [µPKI-CA](https://github.com/proh4cktive/upki-ca) Certification Authority.

### 1.1 Dependencies
The following modules are required
- Flask
- Flask_cors
- PyYAML
- PyZMQ

Some systems libs & tools are also required, make sure you have them pre-installed. A web server (Nginx only by now) is also required
```bash
sudo apt update
sudo apt -y install build-essential libssl-dev libffi-dev python3-dev python3-pip git nginx
```

## 2. Install
The Installation process require two different phases:

1. clone the current repository
```bash
git clone https://github.com/proh4cktive/upki-ra
cd ./upki-ra
```

2. Install the dependencies and upki-ra service in order to auto-start service on boot if needed. The install script will also setup the auto-generation of CRL and guide you during the setup process of your Registration Authority (RA)
```bash
./install.sh
```

If your CA is running on specific ports you can pass them to install script
```bash
./install.sh -i 127.0.0.1 -p 5000
```

If you have more complex configurations, you will probably need to modify the services and timer scripts in: 
> */etc/systemd/system/upki-*.service *

## 3. Usage
The Registration Authority (RA) is not designed to be used manually, you should use the administration WEB interface [µPKI-WEB](https://github.com/proh4cktive/upki-web) in order to manage profile and certificates.

If needed you can still check options using
```bash
./ra_server.py --help
```

## 3.1 RA registration
Certification Authority can not run alone, you MUST setup a Registration Authority to manage certificate. *The current process generates a specific RA certificate in order to encrypt the communication between CA and RA in near future, but this is not currently set!*
Start the CA in register mode in order to generate a one-time seed value that you will have to reflect on your RA start
```bash
./ra_server.py register
```

## 3.2 Common usage
Once your RA registered you can simply launch your service by calling 'listen' action. This is basically what the services is doing.
```bash
./ra_server.py listen
```

## 3.3 Certificate Revokation List (CRL) generation
In order to validate certificates, CRL are required by most of SSL/TLS clients. You can automatically generate them manually, but the upki-ra-crl services is basically calling the following command.
```bash
./ra_server.py crl
```

## 4. Advanced usage
If you know what you are doing, some more advanced options allows you to setup a specific CA/RA couple.

### 4.1 Change default directory
If you want to change the default directory path ($HOME/.upki) for logs, config and storage, please use the 'dir' flag
```bash
./ra_server.py --dir /my/new/directory/
```

### 4.2 Listening IP:Port
In order to deploy for more serious purpose than just testing, you'll probably ended up with a different server for your CA and RA. You must then specify an IP and a port that must be reflected in your CA configuration.

For RA registration:
```bash
./ra_server --ip X.X.X.X --port 5000
```

For common operations
```bash
./ra_server --ip X.X.X.X --port 5000
```

### 4.3 Listening web IP:Port
If you want to setup a different configuration where your administration web interface interact with different ip address and port you can specify these options.
Remember that this is Nginx that is acting as reverse proxy in default configuration, so your RA never needs to listen on other than localhost in most cases.
```bash
./ra_server.py listen --ip X.X.X.X --port 8000
```

*Note: you can NOT use the same port for CA and WEB listening*

## 5. Help
For more advanced usage please check the app help global
```bash
./ra_server.py --help
```

You can also have specific help for each actions
```bash
./ra_server.py init --help
```

## 4. TODO
Until being ready for production some tasks remains:

> - Setup Unit Tests
> - Refactoring of RegistrationAuthority class
> - Setup ZMQ-TLS encryption between CA and RA
> - Store CA IP:Port in config file
> - Add uninstall.sh script
