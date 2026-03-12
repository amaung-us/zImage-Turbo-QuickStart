## Z-Image-Turbo GGUF

[Back to index](index.md)


### Folder Structure
Clone the repo and place the /srv folder and sub folders under correct location.

```
/srv/
├── apps/
│   ├── zimage-turbo-web/
│   │  └── app.py
│   │  └── templates
│   │      └── index.html
│   │  └──  static/
│   │  └── .venv/
│   ├── zimage-turbo-local/
│   │  └── zit-gguf-t2i.py
│   │  └── requirements.txt
│   │  └── .venv/
│   └── other apps... 
├── models/
│   └── zImage-Turbo/
│      └── orig/
│      └── gguf/

```

run this via terminal to create folder structure listed above:
```bash
sudo mkdir -p /srv/{apps,models}
sudo mkdir -p /srv/apps{zimage-turbo-web,zimage-turbo-webapi,zimage-turbo-local}
sudo mkdir /srv/models/zImage-Turbo
sudo mkdir -p ~/srv/models/zImage-Turbo{orig,gguf}
sudo chown -R $USER:$USER /srv
```

### Download ZImage-Turbo GGUF Quantized


Download Z-Image-Turbo from one of the followings
<br>
*(remember Z-Image-Turbo != Z-Image)*
<br>
HuggingFace CLI: hf download <repo_id> --local-dir <path_to_folder>

```
[Original]
https://huggingface.co/Tongyi-MAI/Z-Image-Turbo

[GGUF Quantized]
https://huggingface.co/jayn7/Z-Image-Turbo-GGUF

```
**Clone this repo. All the files needed are in assets/srv folder.**



---

### Running Local GGUF via Terminal



run the following commands:

```bash
cd /srv/apps/zimage-turbo-local

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip setuptools wheel

python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

python -m pip install -r requirements.txt

```

test by running 

```
python3 zit-gguf-t2i.py
```
---

 ### Local GGUF via Web Interface

 
 run the following commands:
 ```bash
cd /srv/apps/zimage-turbo-web

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip setuptools wheel

python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

python -m pip install -r requirements.txt

 ```
To run the web server:
```
cd /srv/apps/zimage-web
source .venv/bin/activate
uvicorn app:app --host 0.0.0.0 --port 7860
```
Go to the IP address of the machine and try creating images. Try to stay within memory limits. 
```
http://xxx.xxx.xxx.xxx:7860
```
Keep the images around 720p (1280x720) on 12GB card -- 4 Passes will work just fine.


### Create System Service to start web server

Create a systemd service:
```
sudo nano /etc/systemd/system/zimage-web.service
```
Paste:
```
[Unit]
Description=ZImage Turbo Web UI
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=radcliffe
Group=radcliffe
WorkingDirectory=/srv/apps/zimage-turbo-web
Environment="PATH=/srv/apps/zimage-turbo-web/.venv/bin"
ExecStart=/srv/apps/zimage-turbo-web/.venv/bin/uvicorn app:app --host 0.0.0.0 --port 7860
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then enable it by:
```
sudo systemctl daemon-reload
sudo systemctl enable zimage-web
sudo systemctl start zimage-web
sudo systemctl status zimage-web
```

---
## Integrated Solution

### All in one - Web + API for Open WebUI (OpenAI Compatible)
Becareful  what you wish for. This solution will push memory to it's limits with 12GB vRAM

 run the following commands:
 ```bash
cd /srv/apps/zimage-turbo-web

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip setuptools wheel

python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

python -m pip install -r requirements.txt

 ```



### Create System Service to start web server

Create a systemd service:
```
sudo nano /etc/systemd/system/zimage-web.service
```
Paste:
```
[Unit]
Description=ZImage Turbo Web UI
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=radcliffe
Group=radcliffe
WorkingDirectory=/srv/apps/zimage-turbo-webapi
Environment="PATH=/srv/apps/zimage-turbo-webapi/.venv/bin"
ExecStart=/srv/apps/zimage-turbo-web/.venv/bin/uvicorn app:app --host 0.0.0.0 --port 7860
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then enable it by:
```
sudo systemctl daemon-reload
sudo systemctl enable zimage-web
sudo systemctl start zimage-web
sudo systemctl status zimage-web
```
