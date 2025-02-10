conda create --name trac_env python=3.9
conda activate trac_env
conda deactivate

pip install -r requirements.txt
pip freeze > requirements.txt