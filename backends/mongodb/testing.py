import numpy as np
from ase.lattice import bulk
from ase.calculators.singlepoint import SinglePointCalculator

from abcd.structurebox import StructureBox
from abcd.authentication import Credentials
import mongobackend.mongobackend as mongobackend


box = StructureBox(mongobackend.MongoDBBackend('localhost', 27017))
token = box.authenticate(Credentials('martin'))

box.remove(token, {}, False)

N = 10
for i in range(N):
    atoms = bulk('Si', crystalstructure='diamond', a=5.43, cubic=True)
    atoms.rattle()

    # simulate a calculation with random results
    e = np.random.uniform()
    f = np.random.uniform(size=3*len(atoms)).reshape((len(atoms), 3))
    s = np.random.uniform(size=9).reshape((3, 3))
    calc = SinglePointCalculator(atoms, energy=e, forces=f, stress=s)
    atoms.set_calculator(calc)
    f = atoms.get_forces()
    e = atoms.get_potential_energy()

    # add some arbitrary data
    atoms.info['integer_info'] = 42
    atoms.info['real_info'] = 217
    atoms.info['config_type'] = 'diamond'
    atoms.new_array('array_data', np.ones_like(atoms.numbers))
    
    box.insert(token, atoms)


for i in box.find(token, {"calculator": "unknown"}):
    print(i)