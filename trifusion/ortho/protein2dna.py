#!/usr/bin/env python2
#
#  Copyright 2012 Unknown <diogo@arch>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#

"""
This module deals with the conversion of protein sequences into their
corresponding nucleotide sequences. Since the conversion from protein to DNA
cannot be made without knowing the nucleotide sequence, this module contains
functions that compile and store DNA sequences, convert them into amino acid
sequences and then tries to match them to the original protein sequences.
"""

from os.path import join
import subprocess

dna_map = {
    'ATA': 'I', 'ATC': 'I', 'ATT': 'I', 'ATG': 'M',
    'ACA': 'T', 'ACC': 'T', 'ACG': 'T', 'ACT': 'T',
    'AAC': 'N', 'AAT': 'N', 'AAA': 'K', 'AAG': 'K',
    'AGC': 'S', 'AGT': 'S', 'AGA': 'R', 'AGG': 'R',
    'CTA': 'L', 'CTC': 'L', 'CTG': 'L', 'CTT': 'L',
    'CCA': 'P', 'CCC': 'P', 'CCG': 'P', 'CCT': 'P',
    'CAC': 'H', 'CAT': 'H', 'CAA': 'Q', 'CAG': 'Q',
    'CGA': 'R', 'CGC': 'R', 'CGG': 'R', 'CGT': 'R',
    'GTA': 'V', 'GTC': 'V', 'GTG': 'V', 'GTT': 'V',
    'GCA': 'A', 'GCC': 'A', 'GCG': 'A', 'GCT': 'A',
    'GAC': 'D', 'GAT': 'D', 'GAA': 'E', 'GAG': 'E',
    'GGA': 'G', 'GGC': 'G', 'GGG': 'G', 'GGT': 'G',
    'TCA': 'S', 'TCC': 'S', 'TCG': 'S', 'TCT': 'S',
    'TTC': 'F', 'TTT': 'F', 'TTA': 'L', 'TTG': 'L',
    'TAC': 'Y', 'TAT': 'Y', 'TAA': '', 'TAG': '',
    'TGC': 'C', 'TGT': 'C', 'TGA': '', 'TGG': 'W'}


def translate(sequence):
    """
    Translates a DNA string into an amino acid sequence
    :param sequence: string. DNA sequence
    :return: String. Protein sequence
    """

    sequence = sequence.lower().replace("-", "")
    aa_sequence = ""

    for i in range(0, len(sequence), 3):
        codon = sequence[i:i + 3]

        # Check if codon is multiple of 3. If not, place an X (missing data)
        if len(codon) == 3:
            # Check if there is missing data on the codon. If so, place an X
            if "n" in codon:
                aa = ""
            else:
                try:
                    aa = dna_map[codon.upper()]
                except KeyError:
                    aa = ""
        else:
            aa = ""

        aa_sequence += aa

    return aa_sequence


def create_db(f_list, dest="./"):
    """
    Creates a fasta database file containing the translated protein sequences
    from the cds files. The final transcripts.fas file will be use
    by USEARCH to get matches between the original protein sequences and their
    nucleotide counterparts. A dictionary database will also be created where
    the transcript headers will be associated with the original DNA sequence,
    so that they will be later retrieved
    :param f_list. List, containing the file names of the transcript files
    """

    output_handle = open(join(dest, "transcripts.fas"), "w")
    id_dic = {}

    for f in f_list:
        handle = open(f, encoding="latin1")
        seq = ""
        header = ""
        for line in handle:
            if line.startswith(">"):
                if seq != "":
                    aa_seq = translate(seq)
                    output_handle.write(">%s\n%s\n" % (header, aa_seq))
                    id_dic[header] = seq

                header = line.strip()[1:].replace(" ", ";;")
                seq = ""
            else:
                seq += line.strip()

    output_handle.close()

    return id_dic


def create_query(input_list, dest="./"):
    """
    To speed things up, all sequences in the input protein files will be
    concatenated into a single file, which will be used as query in USEARCH.
    :param input_list: List, with file names of the protein files to convert
    """

    f_handle = open(join(dest, "query.fas"), "w")
    query_db = {}

    for f in input_list:
        handle = open(f)
        for line in handle:
            if line.startswith(">"):
                query_db[f].append(line.strip()[1:].replace(" ", ";;"))
                f_handle.write(line.replace(" ", ";;"))
            else:
                f_handle.write(line)

        handle.close()

    f_handle.close()

    return query_db


def create_query_from_dict(protein_dict):
    """
    Analogous to create_query, but begins from a dictionary provided by
    processed group files
    :param protein_dict: dictionary
    """

    query_db = {"group": []}
    f_handle = open("query", "w")

    for cl in protein_dict:
        for seq_id, seq in cl:
            query_db[cl].append(seq_id.replace(" ", ";;"))
            f_handle.write(">%s\n%s\n" % (seq_id.replace(" ", ";;"), seq))

    f_handle.close()

    return query_db


def pair_search(dest="./"):
    """
    This will use USEARCH to search for translated transcript sequences
    identical to the original protein files
    """

    query_path = join(dest, "query.fas")
    db_path = join(dest, "transcripts.fas")
    out_path = join(dest, "pairs.out")

    subprocess.Popen(["usearch -usearch_global %s -db %s -id 1 -maxaccepts"
                      " .9 -blast6out %s" % (query_path, db_path, out_path)],
                     shell=True).wait()


def get_pairs(dest="./"):
    """
    Parses the output of USEARCH and creates a dictionary with the header
    pairs between original protein and transcripts
    """

    file_h = open(join(dest, "pairs.out"))
    pair_db = {}

    for l in file_h:
        fields = l.split("\t")
        pair_db[fields[0]] = fields[1]

    file_h.close()
    return pair_db


def convert_protein_file(pairs, query_db, id_db, output_dir,
                         outfile_suffix="_dna.fa"):
    """
    A given protein file will be converted into their corresponding nucleotide
    sequences using a previously set database using the create_db function
    :return:
    """

    bad = 0

    for infile, vals in query_db.items():

        output_file = join(output_dir, infile.split(".")[0] + outfile_suffix)

        f_handle = open(output_file, "w")

        for i in vals:
            if i in pairs:
                seq = id_db[pairs[i]]
                f_handle.write(">%s\n%s\n" % (i.replace(";;", " "), seq))
            else:
                bad += 1


def convert_group(cds_file_list, protein_db, group_sequences,
                  shared_namespace=None):
    """
    Convenience function that wraps all required operations to convert protein
    to nucleotide files from a Group object
    """

    if shared_namespace:
        shared_namespace.act = "Creating database"
    # Create database
    id_db = create_db(cds_file_list)

    if shared_namespace:
        shared_namespace.act = "Creating query"
    # Create query for USEARCH
    seq_dict = group_sequences.retrieve_sequences(protein_db, mode="dict")
    query_db = create_query_from_dict(seq_dict)
    # Execute search

    if shared_namespace:
        shared_namespace.act = "Performing search"
    pair_search()
    pair_db = get_pairs()
    # Convert files

    if shared_namespace:
            shared_namespace.act = "Converting to nucleotide"
    convert_protein_file(pair_db, query_db, id_db)


__author__ = "Diogo N. Silva"
