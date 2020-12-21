#!/usr/bin/env python3
#-*- coding: utf-8 -*-

"""
This module provides class and methods for dealing with RDKit RWMol, Mol.
"""

from typing import Union

from rdkit import Chem
from rdkit.Chem.rdchem import BondType, Mol, RWMol

# openbabel import is currently put behind rdkit.
# This relates to https://github.com/rdkit/rdkit/issues/2292
# For Mac, with anaconda build:
# rdkit -  2020.03.2.0 from rdkit channel
# openbabel -  2.4.1 from rmg channel
# works fine without sequence problem
# For Linux,
# rdkit - 2020.03.3 from rdkit channel
# openbabel - 2.4.1 from rmg channel does not work
import openbabel as ob

# Keep the representation method from rdchem.Mol
KEEP_RDMOL_ATTRIBUTES = ['_repr_html_',
                         '_repr_png_',
                         '_repr_svg_']

# Bond order dictionary for RDKit, numbers are the bond order.
# Note: There is a bond type 'OTHER' which may be helpful to treat TSs
ORDERS = {1: BondType.SINGLE, 2: BondType.DOUBLE, 3: BondType.TRIPLE, 1.5: BondType.AROMATIC,
          4: BondType.QUADRUPLE,
          'S': BondType.SINGLE, 'D': BondType.DOUBLE, 'T': BondType.TRIPLE, 'B': BondType.AROMATIC,
          'Q': BondType.QUADRUPLE}


class RDKitMol(object):
    """
    A helpful wrapper for rdchem.Mol.
    The method nomenclature follows the Camel style to be consistent with RDKit.
    It keeps almost all of the orignal method of Chem.rdchem.Mol/RWMol, but add few useful
    shortcuts, so that a user doesn't need to refer to other RDKit modules.
    """

    def __init__(self, mol: Union[Mol, RWMol]):
        """
        Generate an RDKitMol Molecule instance from a RDKit Chem.rdchem.Mol or RWMol molecule.

        Args:
            mol (Union[Mol, RWMol]): The RDKit Chem.rdchem.Mol / RWmol molecule to be converted.
        """
        # keep the link to original molecule so we can easily recover it if needed.
        if isinstance(mol, Mol):
            self._mol = RWMol(mol)  # Make the original Mol a writable object
        elif isinstance(mol, RWMol):
            self._mol = mol
        else:
            raise ValueError(f'mol should be rdkit.Chem.rdchem.Mol / RWMol. '
                             f'Got: {type(mol)}')

        # Link methods of rdchem.Mol to the new instance
        for attr in dir(self._mol):
            # Not reset private properties and repeated properties
            if not attr.startswith('_') and not hasattr(self, attr):
                setattr(self, attr, getattr(self._mol, attr,))
            elif attr in KEEP_RDMOL_ATTRIBUTES:
                setattr(self, attr, getattr(self._mol, attr,))

        # Set atom map number
        self.SetAtomMapNumbers()

        # Perceive rings
        Chem.GetSymmSSSR(self._mol)

    @ classmethod
    def FromOBMol(cls,
                  ob_mol: 'openbabel.OBMol',
                  remove_h: bool = False,
                  sanitize: bool = True,
                  ) -> 'RDKitMol':
        """
        Convert a OpenBabel molecular structure to an RDKit RDMol object.

        Args:
            ob_mol (Molecule): An OpenBabel Molecule object for the conversion.
            remove_h (bool, optional): Whether to remove hydrogen atoms from the molecule, Defaults to True.
            sanitize (bool, optional): Whether to sanitize the RDKit molecule. Defaults to True.

        Returns:
            RDKitMol: An RDKit molecule object corresponding to the input OpenBabel Molecule object.
        """
        rw_mol = openbabel_mol_to_rdkit_mol(ob_mol, remove_h, sanitize)
        return cls(rw_mol)

    @classmethod
    def FromMol(cls,
                mol: Union[Mol, RWMol],
                ) -> 'RDKitMol':
        """
        Convert a RDKit Chem.rdchem.Mol molecule to RDKitMol Molecule.

        Args:
            rdmol (Union[Mol, RWMol]): The RDKit Chem.rdchem.Mol / RWMol molecule to be converted.

        Returns:
            RDKitMol: An RDKitMol molecule.
        """
        return cls(mol)

    @ classmethod
    def FromSmiles(cls,
                   smiles: str,
                   remove_h: bool = False,
                   sanitize: bool = True,
                   ) -> 'RDKitMol':
        """
        Convert a smiles to an RDkit Mol object.

        Args:
            smiles (str): A SMILES representation of the molecule.
            remove_h (bool, optional): Whether to remove hydrogen atoms from the molecule, ``True`` to remove.
            sanitize (bool, optional): Whether to sanitize the RDKit molecule, ``True`` to sanitize.

        Returns:
            RDKitMol: An RDKit molecule object corresponding to the SMILES.
        """
        mol = Chem.MolFromSmiles(smiles)
        if not remove_h:
            mol = Chem.AddHs(mol)
        if sanitize:
            Chem.SanitizeMol(mol)
        return cls(mol)

    def PrepareOutputMol(self,
                          remove_h: bool = False,
                          sanitize: bool = True,
                          ) -> Mol:
        """
        Generate a RDKit Mol instance for output purpose, to ensure that the original molecule is not modified.

        Args:
            remove_h (bool, optional): Remove less useful explicity H atoms. E.g., When output SMILES, H atoms,
                      if explicitly added, will be included and reduce the readablity. Note, following Hs are not removed:
                        1. H which aren’t connected to a heavy atom. E.g.,[H][H].
                        2. Labelled H. E.g., atoms with atomic number=1, but isotope > 1.
                        3. Two coordinate Hs. E.g., central H in C[H-]C.
                        4. Hs connected to dummy atoms
                        5. Hs that are part of the definition of double bond Stereochemistry.
                        6. Hs that are not connected to anything else.
                        Defaults to False:
            sanitize (bool, optional): whether to sanitize the molecule. Defaults to True.

        Returns:
            Mol: A Mol instance used for output purpose.
        """
        mol = self.GetMol()
        if remove_h:
            mol = Chem.rdmolops.RemoveHs(mol, sanitize=sanitize)
        elif sanitize:
            Chem.rdmolops.SanitizeMol(mol)  # mol is modified in place
        return mol

    def SetAtomMapNumbers(self):
        """
        Set the atom index to atom map number, so atom indexes are shown when plotting the molecule in a 2D graph.
        """
        for ind in range(self.GetNumAtoms()):
            atom = self.GetAtomWithIdx(ind)
            atom.SetProp('molAtomMapNumber', str(atom.GetIdx()))

    def ToOBMol(self):
        """
        Convert RDKitMol to a OBMol.

        Returns:
            OBMol: The corresponding openbabel OBMol.
        """
        return rdkit_mol_to_openbabel_mol(self)

    def ToRWMol(self) -> RWMol:
        """
        Convert the RDKitMol Molecule back to a RDKit Chem.rdchem.RWMol.

        returns:
            RWMol: A RDKit Chem.rdchem.RWMol molecule.
        """
        return self._mol

    def ToSmiles(self,
                 stereo: bool = True,
                 kekule: bool = False,
                 canonical: bool = True,
                 mapid: bool = False,
                 remove_h: bool = True,
                 ) -> str:
        """
        Convert RDKitMol to a SMILES string.

        Args:
            stereo (bool, optional): Whether keep stereochemistry information. Defaults to True.
            kekule (bool, optional): Whether use Kekule form. Defaults to False.
            canonical (bool, optional): Whether generate a canonical SMILES. Defaults to True.
            mapid (bool, optional): Whether to keep map id information in the SMILES. Defaults to False.
            remove_h (bool, optional): Whether to remove H atoms to make obtained SMILES clean. Defaults to True.

        Returns:
            str: The smiles string of the molecule.
        """
        mol = self.PrepareOutputMol(remove_h=remove_h, sanitize=True)

        # Remove atom map numbers, otherwise the smiles string is long and non-readable
        if not mapid:
            for atom in mol.GetAtoms():
                atom.SetAtomMapNum(0)

        return Chem.rdmolfiles.MolToSmiles(mol,
                                           isomericSmiles=stereo,
                                           kekuleSmiles=kekule,
                                           canonical=canonical)


def openbabel_mol_to_rdkit_mol(obmol: 'openbabel.OBMol',
                               remove_h: bool = False,
                               sanitize: bool = True,
                               ) -> 'RDKitMol':
    """
    Convert a OpenBabel molecular structure to a Chem.rdchem.RWMol object.
    Args:
        ob_mol (Molecule): An OpenBabel Molecule object for the conversion.
        remove_h (bool, optional): Whether to remove hydrogen atoms from the molecule, Defaults to True.
        sanitize (bool, optional): Whether to sanitize the RDKit molecule. Defaults to True.

    Returns:
        RWMol: A writable RDKit RWMol instance.
    """
    rw_mol = Chem.rdchem.RWMol()
    for obatom in ob.OBMolAtomIter(obmol):
        atom = Chem.rdchem.Atom(obatom.GetAtomicNum())
        isotope = obatom.GetIsotope()
        if isotope != 0:
            atom.SetIsotope(isotope)
        spin = obatom.GetSpinMultiplicity()
        if spin == 2:  # radical
            atom.SetNumRadicalElectrons(1)
        elif spin in [1, 3]:  # carbene
            # TODO: Not sure if singlet and triplet are distinguished
            atom.SetNumRadicalElectrons(2)
        atom.SetFormalCharge(obatom.GetFormalCharge())
        if not (remove_h and obatom.GetAtomicNum == 1):
            rw_mol.AddAtom(atom)

    for bond in ob.OBMolBondIter(obmol):
        # Atom indexes in Openbael is 1-indexed, so we need to convert them to 0-indexed
        atom1_idx = bond.GetBeginAtomIdx() - 1
        atom2_idx = bond.GetEndAtomIdx() - 1
        # Get the bond order. For aromatic molecules, the bond order is not
        # 1.5 but 1 or 2. Manually set them to 1.5
        bond_order = bond.GetBondOrder() if not bond.IsAromatic() else 1.5

        rw_mol.AddBond(atom1_idx, atom2_idx, ORDERS[bond_order])

    # Rectify the molecule
    if remove_h:
        rw_mol = Chem.RemoveHs(rw_mol, sanitize=sanitize)
    elif sanitize:
        Chem.SanitizeMol(rw_mol)
    return rw_mol


def rdkit_mol_to_openbabel_mol(rdmol: Union[Mol, RWMol]):
    """
    Convert a Mol/RWMol to a Openbabel mol.
    Args:
        rdmol: The RDKit Mol/RWMol object to be converted.

    Returns:
        OBMol: An openbabel OBMol instance.
    """
    obmol = ob.OBMol()
    for rdatom in rdmol.GetAtoms():
        obatom = obmol.NewAtom()
        obatom.SetAtomicNum(rdatom.GetAtomicNum())
        isotope = rdatom.GetIsotope()
        if isotope != 0:
            obatom.SetIsotope(isotope)
        obatom.SetFormalCharge(rdatom.GetFormalCharge())
    bond_type_dict = {BondType.SINGLE: 1,
                      BondType.DOUBLE: 2,
                      BondType.TRIPLE: 3,
                      BondType.QUADRUPLE: 4,
                      BondType.AROMATIC: 5}
    for bond in rdmol.GetBonds():
        atom1_idx = bond.GetBeginAtomIdx() + 1
        atom2_idx = bond.GetEndAtomIdx() + 1
        order = bond_type_dict[bond.GetBondType()]
        obmol.AddBond(atom1_idx, atom2_idx, order)

    obmol.AssignSpinMultiplicity(True)

    return obmol
