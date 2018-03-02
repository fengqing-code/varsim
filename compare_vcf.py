#!/usr/bin/env python

import argparse
import os
import sys
import subprocess
import logging
import shutil
import time
import signal
import tempfile
import pybedtools
import pysam
import utils
LOGGER = None

class VCFComparator(object):
    def __init__(self, prefix, true_vcf, reference, sample, vcfs, exclude_filtered, match_geno, log_to_file):
        self.prefix = prefix
        self.true_vcf = true_vcf
        self.reference = reference
        self.sample = sample
        self.vcfs = vcfs
        self.exclude_filtered = exclude_filtered
        self.match_geno = match_geno
        self.log_to_file = log_to_file
        self.tp,self.fp,self.fn = None, None, None

    def run(self):
        '''
        generate TP, FN, FP
        :return:
        '''
        pass

    def get_tp(self):
        '''
        :return: TP file
        '''
        if not self.tp:
            self.run()
        return self.tp

    def get_fp(self):
        '''
        :return: FP file
        '''
        if not self.fp:
            self.run()
        return self.fp

    def get_fn(self):
        '''
        :return: FN file
        '''
        if not self.fn:
            self.run()
        return self.fn

class VarSimVCFComparator(VCFComparator):
    def run(self):
        '''

        :return:
        '''
        cmd = ['java', '-jar', utils.VARSIMJAR, 'vcfcompare',
           '-prefix', self.prefix, '-true_vcf',
           self.true_vcf,
           '-reference', self.reference,
           ]
        if self.exclude_filtered:
            cmd.append('-exclude_filtered')
        if self.match_geno:
            cmd.append('-match_geno')
        if self.sample:
            cmd.append('-sample')
            cmd.append(self.sample)
        cmd.extend(self.vcfs)
        if self.log_to_file:
            with utils.versatile_open(self.log_to_file, 'a') as logout:
                utils.run_shell_command(cmd, sys.stdout, logout)
        else:
            utils.run_shell_command(cmd, sys.stdout, sys.stderr)
        tp = self.prefix + '_TP.vcf'
        fn = self.prefix + '_FN.vcf'
        fp = self.prefix + '_FP.vcf'
        for i in (tp, fn, fp):
            if not os.path.exists(i):
                raise Exception('{0} was not generated by VarSim vcfcompare. Please check and rerun.'.format(i))
        self.tp, self.fn, self.fp = tp, fn, fp

class RTGVCFComparator(VCFComparator):
    def __init__(self):
        return

def generate_sdf(reference, log):
    '''
    take reference and generate SDF
    :param reference:
    :return:
    '''
    sdf = reference + '.sdf'
    if os.path.exists(sdf):
        LOGGER.info('{0} exists, doing nothing'.format(sdf))
        LOGGER.info('for recreation, please remove or rename {0}'.format(sdf))
        return sdf
    cmd = ['java','-jar',utils.RTGJAR,'format',
           '-o', sdf, reference]
    if log:
        with utils.versatile_open(log, 'a') as logout:
            utils.run_shell_command(cmd, logout, logout)
    else:
        utils.run_shell_command(cmd, sys.stdout, sys.stderr)
    return sdf

def run_varsim(prefix, true_vcf, reference, sample, vcfs, exclude_filtered, match_geno, log_to_file):
    '''
    run varsim vcfcompare
    :param args:
    :return: TP, FN, FP VCF filenames
    '''

    cmd = ['java', '-jar', utils.VARSIMJAR, 'vcfcompare',
           '-prefix', prefix, '-true_vcf',
           true_vcf,
           '-reference', reference,
           ]
    if exclude_filtered:
        cmd.append('-exclude_filtered')
    if match_geno:
        cmd.append('-match_geno')
    if sample:
        cmd.append('-sample')
        cmd.append(args.sample)
    cmd.extend(vcfs)
    if log_to_file:
        with utils.versatile_open(log_to_file, 'a') as logout:
            utils.run_shell_command(cmd, sys.stdout, logout)
    else:
        utils.run_shell_command(cmd, sys.stdout, sys.stderr)
    tp = prefix + '_TP.vcf'
    fn = prefix + '_FN.vcf'
    fp = prefix + '_FP.vcf'
    for i in (tp, fn, fp):
        if not os.path.exists(i):
            raise Exception('{0} was not generated by VarSim vcfcompare'.format(i))
    return tp, fn, fp


# run vcfeval

def process(args):
    '''
    main
    :param args:
    :return:
    '''

    # Setup logging
    FORMAT = '%(levelname)s %(asctime)-15s %(name)-20s %(message)s'
    loglevel = utils.get_loglevel(args.loglevel)
    if args.log_to_file:
        logging.basicConfig(filename=args.log_to_file, filemode="w", level=loglevel, format=FORMAT)
    else:
        logging.basicConfig(level=loglevel, format=FORMAT)

    if len(args.vcfs) > 1:
        raise NotImplementedError('right now only support one prediction VCF. Quick workaround: src/sort_vcf.sh vcf1 vcf2 > merged.vcf')

    global LOGGER
    LOGGER = logging.getLogger(__name__)
    LOGGER.info('working hard ...')

    args.out_dir = os.path.abspath(args.out_dir)
    args.reference = os.path.abspath(args.reference)
    utils.makedirs([args.out_dir])

    varsim_prefix = os.path.join(args.out_dir, 'varsim_compare_results')
    varsim_comparator = VarSimVCFComparator(prefix=varsim_prefix, true_vcf = args.true_vcf, reference = args.reference,
               sample = args.sample, vcfs = args.vcfs,
               exclude_filtered = args.exclude_filtered,
               match_geno = args.match_geno, log_to_file= args.log_to_file)
    varsim_tp, varsim_fn, varsim_fp = varsim_comparator.get_tp(), varsim_comparator.get_fn(), varsim_comparator.get_fp()
    #run vcfeval
    sdf = args.sdf
    if not sdf:
        LOGGER.info("user did not supply SDF-formatted reference, trying to generate one...")
        generate_sdf(args.reference, args.log_to_file)

    '''for vcfeval
    sample column must be present, and not empty
    if single-sample vcf, vcfeval doesn't check if samples match in truth and call
    in multi-sample vcf, sample name must be specified
    right now
    '''
    #run_vcfeval()
    #rm -rf vcfeval_split_snp && /home/guoy28/Downloads/rtg-tools-3.8.4-bdba5ea_install/rtg vcfeval --baseline truth.vcf.gz \
    #--calls compare1.vcf.gz -o vcfeval_split_snp -t ref.sdf --output-mode=annotate --sample xx --squash-ploidy --regions ?? \
    #def run_vcfeval():
    #    '''
    #    run vcfeval
    #    :return:
    #    '''

if __name__ == "__main__":
    utils.check_java()

    main_parser = argparse.ArgumentParser(description="VarSim: A high-fidelity simulation validation framework",
                                          formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    main_parser.add_argument("--reference", metavar="FASTA", help="reference filename", required=True, type=str)
    main_parser.add_argument("--sdf", metavar="SDF", help="SDF formatted reference folder", required=False, type=str, default='')
    main_parser.add_argument("--out_dir", metavar="OUTDIR", help="output folder", required=True, type=str)
    main_parser.add_argument("--vcfs", metavar="VCF", help="variant calls to be evaluated", nargs="+", default=[], required = True)
    main_parser.add_argument("--true_vcf", metavar="VCF", help="Input small variant sampling VCF, usually dbSNP", required = True)
    main_parser.add_argument("--regions", help="BED file to restrict analysis [Optional]", required = False, type=str)
    main_parser.add_argument("--sample", metavar = "SAMPLE", help="sample name", required = False, type=str)
    main_parser.add_argument("--exclude_filtered", action = 'store_true', help="only consider variants with PASS or . in FILTER column", required = False)
    main_parser.add_argument("--match_geno", action = 'store_true', help="compare genotype in addition to alleles", required = False)
    main_parser.add_argument('--version', action='version', version=utils.get_version())
    main_parser.add_argument("--log_to_file", metavar="LOGFILE", help="logfile. If not specified, log to stderr", required=False, type=str, default="")
    main_parser.add_argument("--loglevel", help="Set logging level", choices=["debug", "warn", "info"], default="info")
    main_parser.add_argument("--vcfcompare_options", metavar="OPT", help="additional options for VarSim vcfcompare", default="", type = str)
    main_parser.add_argument("--vcfeval_options", metavar="OPT", help="additional options for RTG vcfeval", default="", type = str)

    args = main_parser.parse_args()
    process(args)