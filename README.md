conda create --name trac_env python=3.9
conda activate trac_env
conda deactivate

pip install -r requirements.txt
pip freeze > requirements.txt

python manage.py makemigrations
python manage.py migrate

python manage.py collectstatic


python manage.py start_modbus
python manage.py runserver

# user login
Data
1@database"# Traceability_BAPL" 
