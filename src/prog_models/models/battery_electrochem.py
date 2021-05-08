# Copyright © 2021 United States Government as represented by the Administrator of the
# National Aeronautics and Space Administration.  All Rights Reserved.

from .. import PrognosticsModel

from math import asinh, log

# Constants of nature
R = 8.3144621;  # universal gas constant, J/K/mol
F = 96487;      # Faraday's constant, C/mol

def update_qmax(params):
    # note qMax = qn+qp
    return {
        'qMax': params['qMobile']/(params['xnMax']-params['xnMin'])
    }

def update_vols(params):
    # Volumes (total volume is 2*P.Vol), assume volume at each electrode is the
    # same and the surface/bulk split is the same for both electrodes
    return {
        'VolS': params['VolSFraction']*params['Vol'],
        'VolB': params['Vol']*(1.0-params['VolSFraction'])
    }

# set up charges (Li ions)
def update_qpmin(params):
    # min charge at pos electrode
    return {
        'qpMin': params['qMax']*params['xpMin'] 
    }

def update_qpmax(params):
    # max charge at pos electrode
    return {
        'qpMax': params['qMax']*params['xpMax'] 
    }

def update_qnmin(params):
    # min charge at negative electrode
    return {
        'qnMin': params['qMax']*params['xnMin'] 
    }

def update_qnmax(params):
    # max charge at negative electrode
    return {
        'qnMax': params['qMax']*params['xnMax'] 
    }

def update_qpSBmin(params):
    # min charge at surface and bulk pos electrode
    return {
        'qpSMin': params['qMax']*params['xpMin']*params['VolSFraction'],
        'qpBMin': params['qMax']*params['xpMin']*(1.0-params['VolSFraction']),
        'x0': {
            **params['x0'],
            'qpS': params['qMax']*params['xpMin']*params['VolSFraction'],
            'qpB': params['qMax']*params['xpMin']*(1.0-params['VolSFraction'])
        }
    }

def update_qpSBmax(params):
    # max charge at surface and pos electrode
    return {
        'qpSMax': params['qMax']*params['xpMax']*params['VolSFraction'],
        'qpBMax': params['qMax']*params['xpMax']*(1.0-params['VolSFraction'])
    }

def update_qnSBmin(params):
    # min charge at surface and bulk pos electrode
    return {
        'qnSMin': params['qMax']*params['xnMin']*params['VolSFraction'],
        'qnBMin': params['qMax']*params['xnMin']*(1.0-params['VolSFraction'])

    }

def update_qnSBmax(params):
    # max charge at surface and pos electrode
    return {
        'qnSMax': params['qMax']*params['xnMax']*params['VolSFraction'],
        'qnBMax': params['qMax']*params['xnMax']*(1.0-params['VolSFraction']),
        'x0': {
            **params['x0'],
            'qnS': params['qMax']*params['xnMax']*params['VolSFraction'],
            'qnB': params['qMax']*params['xnMax']*(1.0-params['VolSFraction'])
        }
    }

def update_qSBmax(params):
    # max charge at surface, bulk (pos and neg)
    return {
        'qSMax': params['qMax']*params['VolSFraction'],
        'qBMax': params['qMax']*(1.0-params['VolSFraction']),
    }

derived_callbacks = {
    'qMobile': [update_qmax],
    'VolSFraction': [update_vols, update_qpSBmin, update_qpSBmax, update_qSBmax],
    'Vol': [update_vols],
    'qMax': [update_qpmin, update_qpmax, update_qpSBmin, update_qpSBmax, update_qnmin, update_qnmax, update_qpSBmin, update_qpSBmax, update_qSBmax],
    'xpMin': [update_qpmin, update_qpSBmin],
    'xpMax': [update_qpmax, update_qpSBmax],
    'xnMin': [update_qmax, update_qnmin, update_qnSBmin],
    'xnMax': [update_qmax, update_qnmax, update_qnSBmax]
}


class BatteryElectroChem(PrognosticsModel):
    """
    Prognostics model for a battery, represented by an electrochemical equations.

    This class implements an Electro chemistry model as described in the following paper:
    `M. Daigle and C. Kulkarni, "Electrochemistry-based Battery Modeling for Prognostics," Annual Conference of the Prognostics and Health Management Society 2013, pp. 249-261, New Orleans, LA, October 2013. http://www.phmsociety.org/node/1054/`

    The default model parameters included are for Li-ion batteries, specifically 18650-type cells. Experimental discharge curves for these cells can be downloaded from the `Prognostics Center of Excellence Data Repository https://ti.arc.nasa.gov/tech/dash/groups/pcoe/prognostic-data-repository/`.

    Events: (1)
        EOD: End of Discharge

    Inputs/Loading: (1)
        i: Current draw on the battery

    States: (8)
        tb, Vo, Vsn, Vsp, qnB, qnS, qpB, qpS

    Outputs/Measurements: (2)
        | t: Temperature of battery (°C) 
        | v: Voltage supplied by battery`

    Model Configuration Parameters:
        | process_noise : Process noise (applied at dx/next_state). 
                    Can be number (e.g., .2) applied to every state, a dictionary of values for each 
                    state (e.g., {'x1': 0.2, 'x2': 0.3}), or a function (x) -> x
        | process_noise_dist : Optional, distribution for process noise (e.g., normal, uniform, triangular)
        | measurement_noise : Measurement noise (applied in output eqn)
                    Can be number (e.g., .2) applied to every output, a dictionary of values for each 
                    output (e.g., {'z1': 0.2, 'z2': 0.3}), or a function (z) -> z
        | measurement_noise_dist : Optional, distribution for measurement noise (e.g., normal, uniform, triangular)
        | qMobile :
        | xnMax : Maximum mole fraction (neg electrode)
        | xnMin : Minimum mole fraction (neg electrode)
        | xpMax : Maximum mole fraction (pos electrode)
        | xpMin : Minimum mole fraction (pos electrode) - note xn + xp = 1
        | Ro : for Ohmic drop (current collector resistances plus electrolyte resistance plus solid phase resistances at anode and cathode)
        | alpha : anodic/cathodic electrochemical transfer coefficient
        | Sn : Surface area (- electrode) 
        | Sp : Surface area (+ electrode)
        | kn : lumped constant for BV (- electrode)
        | kp : lumped constant for BV (+ electrode)
        | Vol : total interior battery volume/2 (for computing concentrations)
        | VolSFraction : fraction of total volume occupied by surface volume
        | tDiffusion : diffusion time constant (increasing this causes decrease in diffusion rate)
        | to : for Ohmic voltage
        | tsn : for surface overpotential (neg)
        | tsp : for surface overpotential (pos)
        | U0p : Redlich-Kister parameter (+ electrode)
        | Ap : Redlich-Kister parameters (+ electrode)
        | U0n : Redlich-Kister parameter (- electrode)
        | An : Redlich-Kister parameters (- electrode)
        | VEOD : End of Discharge Voltage Threshold
        | x0 : Initial state
    """
    events = ['EOD']
    inputs = ['i']
    states = ['tb', 'Vo', 'Vsn', 'Vsp', 'qnB', 'qnS', 'qpB', 'qpS']
    outputs = ['t', 'v']

    default_parameters = {  # Set to defaults
        'qMobile': 7600,
        'xnMax': 0.6,
        'xnMin': 0,
        'xpMax': 1.0,
        'xpMin': 0.4,
        'Ro': 0.117215,
        
        # Li-ion parameters
        'alpha': 0.5,
        'Sn': 0.000437545,
        'Sp': 0.00030962,
        'kn': 2120.96,
        'kp': 248898,
        'Vol': 2e-5,
        'VolSFraction': 0.1,

        # time constants
        'tDiffusion': 7e6,
        'to': 6.08671,
        'tsn': 1001.38,
        'tsp': 46.4311,

        # Redlich-Kister parameters (+ electrode)
        'U0p': 4.03,
        'Ap': [-31593.7, 0.106747, 24606.4, -78561.9, 13317.9, 307387, 84916.1, -1.07469e+06, 2285.04, 990894, 283920, -161513, -469218],

        # Redlich-Kister parameters (- electrode)
        'U0n': 0.01,
        'An': [86.19, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],

        'x0': {
            'Vo': 0,
            'Vsn': 0,
            'Vsp': 0,
            'tb': 292.1  # in K, about 18.95 C
        },

        'process_noise': 1e-3,

        # End of discharge voltage threshold
        'VEOD': 3.0
    }

    def get_derived_callbacks(self):
        return derived_callbacks

    def initialize(self, u = {}, z = {}):
        return self.parameters['x0']

    def dx(self, x, u):
        params = self.parameters
        # Negative Surface
        CnBulk = x['qnB']/params['VolB']
        CnSurface = x['qnS']/params['VolS']
        xnS = x['qnS']/params['qSMax']

        qdotDiffusionBSn = (CnBulk-CnSurface)/params['tDiffusion']

        Jn = u['i']/params['Sn']
        Jn0 = params['kn']*((1-xnS)*xnS)**params['alpha']

        v_part = R*x['tb']/F/params['alpha']

        VsnNominal = v_part*asinh(Jn/(2*Jn0))
        Vsndot = (VsnNominal-x['Vsn'])/params['tsn']

        # Positive Surface
        CpBulk = x['qpB']/params['VolB']
        CpSurface = x['qpS']/params['VolS']
        xpS = x['qpS']/params['qSMax']
        
        qdotDiffusionBSp = (CpBulk-CpSurface)/params['tDiffusion']
        qpBdot = -qdotDiffusionBSp
        qpSdot = u['i'] + qdotDiffusionBSp

        Jp = u['i']/params['Sp']
        Jp0 = params['kp']*((1-xpS)*xpS)**params['alpha']

        VspNominal = v_part*asinh(Jp/(2*Jp0))
        Vspdot = (VspNominal-x['Vsp'])/params['tsp']

        # Combined
        VoNominal = u['i']*params['Ro']
        Vodot = (VoNominal-x['Vo'])/params['to']

        return self.apply_process_noise({
            'tb': 0,
            'Vo': Vodot,
            'Vsn': Vsndot,
            'Vsp': Vspdot,
            'qnB': -qdotDiffusionBSn,
            'qnS': qdotDiffusionBSn - u['i'],
            'qpB': qpBdot,
            'qpS': qpSdot
        })
        
    def event_state(self, x):
        return {
            'EOD': (x['qnS'] + x['qnB'])/self.parameters['qnMax']
        }

    def output(self, x):
        # Negative Surface
        xnS = x['qnS']/self.parameters['qSMax']
        VenParts = [
            self.parameters['An'][0] *(2*xnS-1)/F,  # Ven0
            self.parameters['An'][1] *((2*xnS-1)**2  - (2 *xnS*(1-xnS)))/F,  # Ven1
            self.parameters['An'][2] *((2*xnS-1)**3  - (4 *xnS*(1-xnS))*(2*xnS-1))/F,  #Ven2
            self.parameters['An'][3] *((2*xnS-1)**4  - (6 *xnS*(1-xnS))*(2*xnS-1)**2) /F,  #Ven3
            self.parameters['An'][4] *((2*xnS-1)**5  - (8 *xnS*(1-xnS))*(2*xnS-1)**3) /F,  #Ven4
            self.parameters['An'][5] *((2*xnS-1)**6  - (10*xnS*(1-xnS))*(2*xnS-1)**4) /F,  #Ven5
            self.parameters['An'][6] *((2*xnS-1)**7  - (12*xnS*(1-xnS))*(2*xnS-1)**5) /F,  #Ven6
            self.parameters['An'][7] *((2*xnS-1)**8  - (14*xnS*(1-xnS))*(2*xnS-1)**6) /F,  #Ven7
            self.parameters['An'][8] *((2*xnS-1)**9  - (16*xnS*(1-xnS))*(2*xnS-1)**7) /F,  #Ven8
            self.parameters['An'][9] *((2*xnS-1)**10 - (18*xnS*(1-xnS))*(2*xnS-1)**8) /F,  #Ven9
            self.parameters['An'][10]*((2*xnS-1)**11 - (20*xnS*(1-xnS))*(2*xnS-1)**9) /F,  #Ven10
            self.parameters['An'][11]*((2*xnS-1)**12 - (22*xnS*(1-xnS))*(2*xnS-1)**10)/F,  #Ven11
            self.parameters['An'][12]*((2*xnS-1)**13 - (24*xnS*(1-xnS))*(2*xnS-1)**11)/F   #Ven12
        ]
        Ven = self.parameters['U0n'] + R*x['tb']/F*log((1-xnS)/xnS) + sum(VenParts)

        # Positive Surface
        xpS = x['qpS']/self.parameters['qSMax']
        VepParts = [
            self.parameters['Ap'][0] *(2*xpS-1)/F,  #Vep0
            self.parameters['Ap'][1] *((2*xpS-1)**2  - (2 *xpS*(1-xpS)))/F,  #Vep1
            self.parameters['Ap'][2] *((2*xpS-1)**3  - (4 *xpS*(1-xpS))/(2*xpS-1)**(-1)) /F,  #Vep2
            self.parameters['Ap'][3] *((2*xpS-1)**4  - (6 *xpS*(1-xpS))/(2*xpS-1)**(-2)) /F,  #Vep3
            self.parameters['Ap'][4] *((2*xpS-1)**5  - (8 *xpS*(1-xpS))/(2*xpS-1)**(-3)) /F,  #Vep4
            self.parameters['Ap'][5] *((2*xpS-1)**6  - (10*xpS*(1-xpS))/(2*xpS-1)**(-4)) /F,  #Vep5
            self.parameters['Ap'][6] *((2*xpS-1)**7  - (12*xpS*(1-xpS))/(2*xpS-1)**(-5)) /F,  #Vep6
            self.parameters['Ap'][7] *((2*xpS-1)**8  - (14*xpS*(1-xpS))/(2*xpS-1)**(-6)) /F,  #Vep7
            self.parameters['Ap'][8] *((2*xpS-1)**9  - (16*xpS*(1-xpS))/(2*xpS-1)**(-7)) /F,  #Vep8
            self.parameters['Ap'][9] *((2*xpS-1)**10 - (18*xpS*(1-xpS))/(2*xpS-1)**(-8)) /F,  #Vep9
            self.parameters['Ap'][10]*((2*xpS-1)**11 - (20*xpS*(1-xpS))/(2*xpS-1)**(-9)) /F,  #Vep10
            self.parameters['Ap'][11]*((2*xpS-1)**12 - (22*xpS*(1-xpS))/(2*xpS-1)**(-10))/F,  #Vep11
            self.parameters['Ap'][12]*((2*xpS-1)**13 - (24*xpS*(1-xpS))/(2*xpS-1)**(-11))/F   #Vep12
        ]
        Vep = self.parameters['U0p'] + R*x['tb']/F*log((1-xpS)/xpS) + sum(VepParts)

        return self.apply_measurement_noise({
            't': x['tb'] - 273.15,
            'v': Vep - Ven - x['Vo'] - x['Vsn'] - x['Vsp']
        })

    def threshold_met(self, x):
        z = self.output(x)

        # Return true if voltage is less than the voltage threshold
        return {
             'EOD': z['v'] < self.parameters['VEOD']
        }

class BatteryElectroChemEOL(PrognosticsModel):
    states = ['qMax', 'Ro', 'D']
    events = ['InsufficientCapacity']
    inputs = ['i']
    outputs = []

    default_parameters = {
        'x0': {
            'qMax': 7600,
            'Ro': 0.117215,
            'D': 7e6
        },
        'wq': -1e-2,
        'wr': 1e-2,
        'wd': 1e-2,
        'qMaxThreshold': 3800
    }

    def initialize(self, u = {}, z = {}):
        return self.parameters['x0']

    def dx(self, x, u):
        params = self.parameters

        return {
            'qMax': params['wq'] * abs(u['i']),
            'Ro': params['wr'] * abs(u['i']),
            'D': params['wd'] * abs(u['i'])
        }

    def event_state(self, x):
        e_state = (x['qMax']-self.parameters['qMaxThreshold'])/(self.parameters['x0']['qMax']-self.parameters['qMaxThreshold'])
        return {'InsufficientCapacity': max(min(e_state, 1.0), 0.0)}

    def threshold_met(self, x):
        return {'InsufficientCapacity': x['qMax'] < self.parameters['qMaxThreshold']}

    def output(self, x):
        return []

def merge_dicts(a : dict, b : dict):
    """Merge dict b into a"""
    for key in b:
        if key in a and isinstance(a[key], dict) and isinstance(b[key], dict):
            merge_dicts(a[key], b[key])
        else:
            a[key] = b[key]

Battery = BatteryElectroChem
class BatteryElectroChemEODEOL(BatteryElectroChemEOL, Battery):
    inputs = Battery.inputs
    outputs = Battery.outputs
    states = Battery.states + BatteryElectroChemEOL.states
    events = Battery.events + BatteryElectroChemEOL.events

    default_parameters = Battery.default_parameters
    merge_dicts(default_parameters,
        BatteryElectroChemEOL.default_parameters)

    def initialize(self, u = {}, z = {}):
        return self.parameters['x0']

    def dx(self, x, u):
        params = self.parameters

        # TODO(CT): Set parameters from EOD model
        # self.parameters['qMobile'] = x['qMax']* (params['xnMax'] - params['xnMin'])
        # # Make sure it's actually resetting qMax
        # # Consider ability to register callback for derived params
        # self.parameters['Ro'] = x['Ro']
        # self.parameters['tDiffusion'] = x['D']
        
        # Calculate 
        x_dot = Battery.dx(self, x, u)
        x_dot.update(BatteryElectroChemEOL.dx(self, x, u))
        return x_dot

    def output(self, x):
        params = self.parameters
        # TODO(CT): Set parameters from EOD model
        # self.parameters['qMobile'] = x['qMax']* (params['xnMax'] - params['xnMin'])
        # # Make sure it's actually resetting qMax
        # # Consider ability to register callback for derived params
        # self.parameters['Ro'] = x['Ro']
        # self.parameters['tDiffusion'] = x['D']
        
        return Battery.output(self, x)

    def event_state(self, x):
        e_state = Battery.event_state(self, x)
        e_state.update(BatteryElectroChemEOL.event_state(self, x))
        return e_state

    def threshold_met(self, x):
        t_met = Battery.threshold_met(self, x)
        t_met.update(BatteryElectroChemEOL.threshold_met(self, x))
        return t_met