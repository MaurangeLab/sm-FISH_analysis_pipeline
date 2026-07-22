#This code was made almost entirely by AI to save time
import subprocess
import sys

def run(cmd):
    print(f"\n>>> {cmd}")
    result = subprocess.run(cmd, shell=True, text=True)
    if result.returncode != 0:
        print(f"ERREUR sur : {cmd}")
        sys.exit(1)

print("=== Création de l'environnement spots_analysis ===")
run("conda create --name spots_analysis python==3.10 -y")
run("conda run -n spots_analysis pip install spyder-kernels==3.1.4")
run("conda run -n spots_analysis pip install tifffile openpyxl matplotlib pandas czifile aicspylibczi imagio")
run("conda run -n spots_analysis pip install numpy==1.26.4")
run("conda run -n spots_analysis pip install -U scikit-learn")

print("\n=== Création de l'environnement segment ===")
run("conda create --name segment python==3.13 -y")
run("conda run -n segment pip install spyder-kernels==3.1.4")
run("conda run -n segment pip install cellpose==2.2.3")
run("conda run -n segment pip install matplotlib tifffile")
run("conda run -n segment pip install numpy==2.4.6")

print("\n=== Création de l'environnement chinmospots ===")
run("conda create --name chinmospots python==3.10 -y")
run("conda run -n segment pip install spyder-kernels==3.1.4")
run("conda run -n chinmospots pip install epyseg fishdist matplotlib pandas tifffile")
run("conda run -n chinmospots pip install numpy==1.26.3")

print("\n=== Tous les environnements sont prêts ===")
