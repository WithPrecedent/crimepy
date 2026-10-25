"""The labels of the codes in the NIBRS master files.

Each codebook maps the codes of a field (as they are written in the master
files) to their labels. The labels follow the reference tables that the FBI's
Crime Data Explorer publishes with its NIBRS downloads (such as
"NIBRS_OFFENSE_TYPE.csv"), and, for the fields that are only in the master
files (such as the batch header's population group), the FBI's "NIBRS
Flatfile Yearly Master Record Descriptions".

Codes changed over the years, and each codebook has every code that any year
uses. A few codes meant something else in earlier years:

* Race "A" was "Asian or Pacific Islander" before 2013, when "P" (Native
  Hawaiian or Other Pacific Islander) was added.
* Exceptional clearance "C" was "Extradition Denied" in the 1995 document
  and is "In Custody of Other Jurisdiction" now.

Contents:
    CODEBOOKS: every codebook, by the name that `crimepy.nibrs.layouts.Field`
        uses.
    OFFENSE_CATEGORIES: the category of each offense code (such as "Assault
        Offenses").
    CRIMES_AGAINST: whom or what each offense is against ("Person",
        "Property", "Society", or "Not a Crime").
    OFFENSE_GROUPS: whether each offense is in Group "A" or Group "B".
    STATES: the postal abbreviation of each numeric state code.
    STATE_NAMES: the name of each numeric state code.
    AGE_YEARS: the age in years of each special age code.

"""

from __future__ import annotations

from collections.abc import Mapping

# Offense codes, with their name, category, and whom or what they are against.
_OFFENSES: dict[str, tuple[str, str, str, str]] = {
    '09A': ('Murder and Nonnegligent Manslaughter', 'Homicide Offenses', 'Person', 'A'),
    '09B': ('Negligent Manslaughter', 'Homicide Offenses', 'Person', 'A'),
    '09C': ('Justifiable Homicide', 'Homicide Offenses', 'Person', 'A'),
    '100': ('Kidnapping/Abduction', 'Kidnapping/Abduction', 'Person', 'A'),
    '101': ('Treason', 'Other Offenses', 'Society', 'A'),
    '103': ('Espionage', 'Other Offenses', 'Society', 'A'),
    '11A': ('Rape', 'Sex Offenses', 'Person', 'A'),
    '11B': ('Sodomy', 'Sex Offenses', 'Person', 'A'),
    '11C': ('Sexual Assault With An Object', 'Sex Offenses', 'Person', 'A'),
    '11D': ('Criminal Sexual Contact', 'Sex Offenses', 'Person', 'A'),
    '120': ('Robbery', 'Robbery', 'Property', 'A'),
    '13A': ('Aggravated Assault', 'Assault Offenses', 'Person', 'A'),
    '13B': ('Simple Assault', 'Assault Offenses', 'Person', 'A'),
    '13C': ('Intimidation', 'Assault Offenses', 'Person', 'A'),
    '200': ('Arson', 'Arson', 'Property', 'A'),
    '210': ('Extortion/Blackmail', 'Extortion/Blackmail', 'Property', 'A'),
    '220': ('Burglary/Breaking & Entering', 'Burglary/Breaking & Entering', 'Property', 'A'),
    '23A': ('Pocket-picking', 'Larceny/Theft Offenses', 'Property', 'A'),
    '23B': ('Purse-snatching', 'Larceny/Theft Offenses', 'Property', 'A'),
    '23C': ('Shoplifting', 'Larceny/Theft Offenses', 'Property', 'A'),
    '23D': ('Theft From Building', 'Larceny/Theft Offenses', 'Property', 'A'),
    '23E': ('Theft From Coin-Operated Machine or Device', 'Larceny/Theft Offenses', 'Property', 'A'),
    '23F': ('Theft From Motor Vehicle', 'Larceny/Theft Offenses', 'Property', 'A'),
    '23G': ('Theft of Motor Vehicle Parts or Accessories', 'Larceny/Theft Offenses', 'Property', 'A'),
    '23H': ('All Other Larceny', 'Larceny/Theft Offenses', 'Property', 'A'),
    '240': ('Motor Vehicle Theft', 'Motor Vehicle Theft', 'Property', 'A'),
    '250': ('Counterfeiting/Forgery', 'Counterfeiting/Forgery', 'Property', 'A'),
    '26A': ('False Pretenses/Swindle/Confidence Game', 'Fraud Offenses', 'Property', 'A'),
    '26B': ('Credit Card/Automated Teller Machine Fraud', 'Fraud Offenses', 'Property', 'A'),
    '26C': ('Impersonation', 'Fraud Offenses', 'Property', 'A'),
    '26D': ('Welfare Fraud', 'Fraud Offenses', 'Property', 'A'),
    '26E': ('Wire Fraud', 'Fraud Offenses', 'Property', 'A'),
    '26F': ('Identity Theft', 'Fraud Offenses', 'Property', 'A'),
    '26G': ('Hacking/Computer Invasion', 'Fraud Offenses', 'Property', 'A'),
    '26H': ('Money Laundering', 'Other Offenses', 'Society', 'A'),
    '270': ('Embezzlement', 'Embezzlement', 'Property', 'A'),
    '280': ('Stolen Property Offenses', 'Stolen Property Offenses', 'Property', 'A'),
    '290': ('Destruction/Damage/Vandalism of Property', 'Destruction/Damage/Vandalism of Property', 'Property', 'A'),
    '30A': ('Illegal Entry into the United States', 'Other Offenses', 'Society', 'A'),
    '30B': ('False Citizenship', 'Other Offenses', 'Society', 'A'),
    '30C': ('Smuggling Aliens', 'Other Offenses', 'Society', 'A'),
    '30D': ('Re-entry after Deportation', 'Other Offenses', 'Society', 'A'),
    '35A': ('Drug/Narcotic Violations', 'Drug/Narcotic Offenses', 'Society', 'A'),
    '35B': ('Drug Equipment Violations', 'Drug/Narcotic Offenses', 'Society', 'A'),
    '360': ('Failure to Register as a Sex Offender', 'Other Offenses', 'Society', 'A'),
    '36A': ('Incest', 'Sex Offenses, Non-forcible', 'Person', 'A'),
    '36B': ('Statutory Rape', 'Sex Offenses, Non-forcible', 'Person', 'A'),
    '370': ('Pornography/Obscene Material', 'Pornography/Obscene Material', 'Society', 'A'),
    '39A': ('Betting/Wagering', 'Gambling Offenses', 'Society', 'A'),
    '39B': ('Operating/Promoting/Assisting Gambling', 'Gambling Offenses', 'Society', 'A'),
    '39C': ('Gambling Equipment Violation', 'Gambling Offenses', 'Society', 'A'),
    '39D': ('Sports Tampering', 'Gambling Offenses', 'Society', 'A'),
    '40A': ('Prostitution', 'Prostitution Offenses', 'Society', 'A'),
    '40B': ('Assisting or Promoting Prostitution', 'Prostitution Offenses', 'Society', 'A'),
    '40C': ('Purchasing Prostitution', 'Prostitution Offenses', 'Society', 'A'),
    '49A': ('Harboring Escapee/Concealing from Arrest', 'Other Offenses', 'Society', 'A'),
    '49B': ('Flight to Avoid Prosecution', 'Other Offenses', 'Society', 'A'),
    '49C': ('Flight to Avoid Deportation', 'Other Offenses', 'Society', 'A'),
    '510': ('Bribery', 'Bribery', 'Property', 'A'),
    '520': ('Weapon Law Violations', 'Weapon Law Violations', 'Society', 'A'),
    '521': ('Violation of National Firearm Act of 1934', 'Other Offenses', 'Society', 'A'),
    '522': ('Weapons of Mass Destruction', 'Other Offenses', 'Society', 'A'),
    '526': ('Explosives Violation', 'Other Offenses', 'Society', 'A'),
    '58A': ('Import Violations', 'Other Offenses', 'Society', 'A'),
    '58B': ('Export Violations', 'Other Offenses', 'Society', 'A'),
    '61A': ('Federal Liquor Offenses', 'Other Offenses', 'Society', 'A'),
    '61B': ('Federal Tobacco Offenses', 'Other Offenses', 'Society', 'A'),
    '620': ('Wildlife Trafficking', 'Other Offenses', 'Society', 'A'),
    '64A': ('Human Trafficking, Commercial Sex Acts', 'Human Trafficking', 'Person', 'A'),
    '64B': ('Human Trafficking, Involuntary Servitude', 'Human Trafficking', 'Person', 'A'),
    '720': ('Animal Cruelty', 'Animal Cruelty', 'Society', 'A'),
    '90A': ('Bad Checks', 'Bad Checks', 'Property', 'B'),
    '90B': ('Curfew/Loitering/Vagrancy Violations', 'Curfew/Loitering/Vagrancy Violations', 'Society', 'B'),
    '90C': ('Disorderly Conduct', 'Disorderly Conduct', 'Society', 'B'),
    '90D': ('Driving Under the Influence', 'Driving Under the Influence', 'Society', 'B'),
    '90E': ('Drunkenness', 'Drunkenness', 'Society', 'B'),
    '90F': ('Family Offenses, Nonviolent', 'Family Offenses, Nonviolent', 'Person', 'B'),
    '90G': ('Liquor Law Violations', 'Liquor Law Violations', 'Society', 'B'),
    '90H': ('Peeping Tom', 'Peeping Tom', 'Person', 'B'),
    '90I': ('Runaway', 'Other Offenses', 'Not a Crime', 'B'),
    '90J': ('Trespass of Real Property', 'Trespass of Real Property', 'Society', 'B'),
    '90K': ('Failure to Appear', 'Other Offenses', 'Society', 'B'),
    '90L': ('Federal Resource Violations', 'Other Offenses', 'Society', 'B'),
    '90M': ('Perjury', 'Other Offenses', 'Society', 'B'),
    '90Z': ('All Other Offenses', 'All Other Offenses', 'Society', 'B')}

OFFENSE_CATEGORIES: dict[str, str] = {
    k: v[1] for k, v in _OFFENSES.items()}
CRIMES_AGAINST: dict[str, str] = {k: v[2] for k, v in _OFFENSES.items()}
OFFENSE_GROUPS: dict[str, str] = {k: v[3] for k, v in _OFFENSES.items()}

# Numeric state codes, with their postal abbreviation and name. The ORIs of
# Nebraska begin with "NB" and those of Guam with "GM", but their postal
# abbreviations are used here.
_STATES: dict[str, tuple[str, str]] = {
    '01': ('AL', 'Alabama'),
    '02': ('AZ', 'Arizona'),
    '03': ('AR', 'Arkansas'),
    '04': ('CA', 'California'),
    '05': ('CO', 'Colorado'),
    '06': ('CT', 'Connecticut'),
    '07': ('DE', 'Delaware'),
    '08': ('DC', 'District of Columbia'),
    '09': ('FL', 'Florida'),
    '10': ('GA', 'Georgia'),
    '11': ('ID', 'Idaho'),
    '12': ('IL', 'Illinois'),
    '13': ('IN', 'Indiana'),
    '14': ('IA', 'Iowa'),
    '15': ('KS', 'Kansas'),
    '16': ('KY', 'Kentucky'),
    '17': ('LA', 'Louisiana'),
    '18': ('ME', 'Maine'),
    '19': ('MD', 'Maryland'),
    '20': ('MA', 'Massachusetts'),
    '21': ('MI', 'Michigan'),
    '22': ('MN', 'Minnesota'),
    '23': ('MS', 'Mississippi'),
    '24': ('MO', 'Missouri'),
    '25': ('MT', 'Montana'),
    '26': ('NE', 'Nebraska'),
    '27': ('NV', 'Nevada'),
    '28': ('NH', 'New Hampshire'),
    '29': ('NJ', 'New Jersey'),
    '30': ('NM', 'New Mexico'),
    '31': ('NY', 'New York'),
    '32': ('NC', 'North Carolina'),
    '33': ('ND', 'North Dakota'),
    '34': ('OH', 'Ohio'),
    '35': ('OK', 'Oklahoma'),
    '36': ('OR', 'Oregon'),
    '37': ('PA', 'Pennsylvania'),
    '38': ('RI', 'Rhode Island'),
    '39': ('SC', 'South Carolina'),
    '40': ('SD', 'South Dakota'),
    '41': ('TN', 'Tennessee'),
    '42': ('TX', 'Texas'),
    '43': ('UT', 'Utah'),
    '44': ('VT', 'Vermont'),
    '45': ('VA', 'Virginia'),
    '46': ('WA', 'Washington'),
    '47': ('WV', 'West Virginia'),
    '48': ('WI', 'Wisconsin'),
    '49': ('WY', 'Wyoming'),
    '50': ('AK', 'Alaska'),
    '51': ('HI', 'Hawaii'),
    '52': ('CZ', 'Canal Zone'),
    '53': ('PR', 'Puerto Rico'),
    '54': ('AS', 'American Samoa'),
    '55': ('GU', 'Guam'),
    '62': ('VI', 'U.S. Virgin Islands'),
    '69': ('MP', 'Mariana Islands'),
    '98': ('FS', 'Federal'),
    '99': ('OT', 'Other')}

STATES: dict[str, str] = {k: v[0] for k, v in _STATES.items()}
STATE_NAMES: dict[str, str] = {k: v[1] for k, v in _STATES.items()}

# Ages in years of the age codes that are not a number of years. "00" is an
# unknown age, and "99" is 99 years old or older.
AGE_YEARS: dict[str, float | None] = {
    'NN': 0.0, 'NB': 0.0, 'BB': 0.0, '00': None}

_AGES: dict[str, str] = {
    'NN': 'Under 24 Hours',
    'NB': '1-6 Days Old',
    'BB': '7-364 Days Old',
    '00': 'Unknown',
    **{f'{n:02d}': f'{n} Years Old' for n in range(1, 99)},
    '99': 'Over 98 Years Old'}

_ACTIVITIES: dict[str, str] = {
    'A': 'Simple/Gross Neglect',
    'B': 'Buying/Receiving',
    'C': 'Cultivating/Manufacturing/Publishing',
    'D': 'Distributing/Selling',
    'E': 'Exploiting Children',
    'F': 'Organized Abuse',
    'G': 'Other Gang',
    'I': 'Intentional Abuse and Torture',
    'J': 'Juvenile Gang',
    'N': 'None/Unknown',
    'O': 'Operating/Promoting/Assisting/Abetting',
    'P': 'Possessing/Concealing',
    'S': 'Animal Sexual Abuse',
    'T': 'Transporting/Transmitting/Importing',
    'U': 'Using/Consuming',
    'W': 'Conspiracy'}

_AGENCY_TYPES: dict[str, str] = {
    '0': 'Covered by Another Agency',
    '1': 'City',
    '2': 'County',
    '3': 'University or College',
    '4': 'State Police',
    '6': 'Other State Agency',
    '7': 'Tribal',
    '8': 'Federal'}

_ARREST_TYPES: dict[str, str] = {
    'O': 'On View',
    'S': 'Summoned/Cited',
    'T': 'Taken into Custody'}

_BIASES: dict[str, str] = {
    '11': 'Anti-White',
    '12': 'Anti-Black or African American',
    '13': 'Anti-American Indian or Alaska Native',
    '14': 'Anti-Asian',
    '15': 'Anti-Multiple Races, Group',
    '16': 'Anti-Native Hawaiian or Other Pacific Islander',
    '21': 'Anti-Jewish',
    '22': 'Anti-Catholic',
    '23': 'Anti-Protestant',
    '24': 'Anti-Islamic (Muslim)',
    '25': 'Anti-Other Religion',
    '26': 'Anti-Multiple Religions, Group',
    '27': 'Anti-Atheism/Agnosticism',
    '28': 'Anti-Church of Jesus Christ',
    '29': "Anti-Jehovah's Witness",
    '31': 'Anti-Arab',
    '32': 'Anti-Hispanic or Latino',
    '33': 'Anti-Other Race/Ethnicity/Ancestry',
    '41': 'Anti-Gay (Male)',
    '42': 'Anti-Lesbian (Female)',
    '43': 'Anti-Lesbian, Gay, Bisexual, or Transgender (Mixed Group)',
    '44': 'Anti-Heterosexual',
    '45': 'Anti-Bisexual',
    '51': 'Anti-Physical Disability',
    '52': 'Anti-Mental Disability',
    '61': 'Anti-Male',
    '62': 'Anti-Female',
    '71': 'Anti-Transgender',
    '72': 'Anti-Gender Non-Conforming',
    '81': 'Anti-Eastern Orthodox (Russian, Greek, Other)',
    '82': 'Anti-Other Christian',
    '83': 'Anti-Buddhist',
    '84': 'Anti-Hindu',
    '85': 'Anti-Sikh',
    '88': 'None (No Bias)',
    '99': 'Unknown'}

_CIRCUMSTANCES: dict[str, str] = {
    '01': 'Argument',
    '02': 'Assault on Law Enforcement Officer',
    '03': 'Drug Dealing',
    '04': 'Gangland',
    '05': 'Juvenile Gang',
    '06': 'Domestic Violence',
    '07': 'Mercy Killing',
    '08': 'Other Felony Involved',
    '09': 'Other Circumstances',
    '10': 'Unknown Circumstances',
    '20': 'Criminal Killed by Private Citizen',
    '21': 'Criminal Killed by Police Officer',
    '30': 'Child Playing With Weapon',
    '31': 'Gun-Cleaning Accident',
    '32': 'Hunting Accident',
    '33': 'Other Negligent Weapon Handling',
    '34': 'Other Negligent Killings'}

_CLEARANCES: dict[str, str] = {
    'A': 'Death of Offender',
    'B': 'Prosecution Declined',
    'C': 'In Custody of Other Jurisdiction',
    'D': 'Victim Refused to Cooperate',
    'E': 'Juvenile/No Custody',
    'N': 'Not Applicable'}

_COMPLETIONS: dict[str, str] = {'A': 'Attempted', 'C': 'Completed'}

_DISPOSITIONS: dict[str, str] = {
    'H': 'Handled Within Department',
    'R': 'Referred to Other Authorities'}

_DIVISIONS: dict[str, str] = {
    '0': 'Possessions',
    '1': 'New England',
    '2': 'Middle Atlantic',
    '3': 'East North Central',
    '4': 'West North Central',
    '5': 'South Atlantic',
    '6': 'East South Central',
    '7': 'West South Central',
    '8': 'Mountain',
    '9': 'Pacific'}

_DRUGS: dict[str, str] = {
    'A': 'Crack Cocaine',
    'B': 'Cocaine',
    'C': 'Hashish',
    'D': 'Heroin',
    'E': 'Marijuana',
    'F': 'Morphine',
    'G': 'Opium',
    'H': 'Other Narcotics',
    'I': 'LSD',
    'J': 'PCP',
    'K': 'Other Hallucinogens',
    'L': 'Amphetamines/Methamphetamines',
    'M': 'Other Stimulants',
    'N': 'Barbiturates',
    'O': 'Other Depressants',
    'P': 'Other Drugs',
    'U': 'Unknown',
    'X': 'More Than 3 Types'}

_ENTRIES: dict[str, str] = {'F': 'Force', 'N': 'No Force'}

_ETHNICITIES: dict[str, str] = {
    'H': 'Hispanic or Latino',
    'N': 'Not Hispanic or Latino',
    'M': 'Multiple',
    'U': 'Unknown'}

_INJURIES: dict[str, str] = {
    'B': 'Apparent Broken Bones',
    'I': 'Possible Internal Injury',
    'L': 'Severe Laceration',
    'M': 'Apparent Minor Injury',
    'N': 'None',
    'O': 'Other Major Injury',
    'T': 'Loss of Teeth',
    'U': 'Unconsciousness'}

_JUSTIFICATIONS: dict[str, str] = {
    'A': 'Criminal Attacked Police Officer and That Officer Killed Criminal',
    'B': 'Criminal Attacked Police Officer and Criminal Killed by Another Police Officer',
    'C': 'Criminal Attacked a Civilian',
    'D': 'Criminal Attempted Flight From a Crime',
    'E': 'Criminal Killed in Commission of a Crime',
    'F': 'Criminal Resisted Arrest',
    'G': 'Unable to Determine/Not Enough Information'}

_LOCATIONS: dict[str, str] = {
    '01': 'Air/Bus/Train Terminal',
    '02': 'Bank/Savings and Loan',
    '03': 'Bar/Nightclub',
    '04': 'Church/Synagogue/Temple/Mosque',
    '05': 'Commercial/Office Building',
    '06': 'Construction Site',
    '07': 'Convenience Store',
    '08': 'Department/Discount Store',
    '09': "Drug Store/Doctor's Office/Hospital",
    '10': 'Field/Woods',
    '11': 'Government/Public Building',
    '12': 'Grocery/Supermarket',
    '13': 'Highway/Road/Alley/Street/Sidewalk',
    '14': 'Hotel/Motel/Etc.',
    '15': 'Jail/Prison/Penitentiary/Corrections Facility',
    '16': 'Lake/Waterway/Beach',
    '17': 'Liquor Store',
    '18': 'Parking/Drop Lot/Garage',
    '19': 'Rental Storage Facility',
    '20': 'Residence/Home',
    '21': 'Restaurant',
    '22': 'School/College',
    '23': 'Service/Gas Station',
    '24': 'Specialty Store',
    '25': 'Other/Unknown',
    '37': 'Abandoned/Condemned Structure',
    '38': 'Amusement Park',
    '39': 'Arena/Stadium/Fairgrounds/Coliseum',
    '40': 'ATM Separate from Bank',
    '41': 'Auto Dealership New/Used',
    '42': 'Camp/Campground',
    '44': 'Daycare Facility',
    '45': 'Dock/Wharf/Freight/Modal Terminal',
    '46': 'Farm Facility',
    '47': 'Gambling Facility/Casino/Race Track',
    '48': 'Industrial Site',
    '49': 'Military Installation',
    '50': 'Park/Playground',
    '51': 'Rest Area',
    '52': 'School-College/University',
    '53': 'School-Elementary/Secondary',
    '54': 'Shelter-Mission/Homeless',
    '55': 'Shopping Mall',
    '56': 'Tribal Lands',
    '57': 'Community Center',
    '58': 'Cyberspace'}

_LOSSES: dict[str, str] = {
    '1': 'None',
    '2': 'Burned',
    '3': 'Counterfeited/Forged',
    '4': 'Destroyed/Damaged/Vandalized',
    '5': 'Recovered',
    '6': 'Seized',
    '7': 'Stolen/Etc.',
    '8': 'Unknown'}

_MEASURES: dict[str, str] = {
    'GM': 'Gram',
    'KG': 'Kilogram',
    'OZ': 'Ounce',
    'LB': 'Pound',
    'ML': 'Milliliter',
    'LT': 'Liter',
    'FO': 'Fluid Ounce',
    'GL': 'Gallon',
    'DU': 'Dosage Unit',
    'NP': 'Number of Plants',
    'XX': 'Not Reported'}

_MULTIPLE_ARRESTEES: dict[str, str] = {
    'C': 'Count Arrestee',
    'M': 'Multiple',
    'N': 'Not Applicable'}

_OFFICER_ACTIVITIES: dict[str, str] = {
    '01': 'Responding to Disturbance Call',
    '02': 'Burglaries in Progress or Pursuing Burglary Suspects',
    '03': 'Robberies in Progress or Pursuing Robbery Suspects',
    '04': 'Attempting Other Arrests',
    '05': 'Civil Disorder',
    '06': 'Handling, Transporting, Custody of Prisoners',
    '07': 'Investigating Suspicious Persons or Circumstances',
    '08': 'Ambush - No Warning',
    '09': 'Handling Persons with Mental Illness',
    '10': 'Traffic Pursuits and Stops',
    '11': 'All Other'}

_OFFICER_ASSIGNMENTS: dict[str, str] = {
    'F': 'Two-Officer Vehicle',
    'G': 'One-Officer Vehicle (Alone)',
    'H': 'One-Officer Vehicle (Assisted)',
    'I': 'Detective or Special Assignment (Alone)',
    'J': 'Detective or Special Assignment (Assisted)',
    'K': 'Other (Alone)',
    'L': 'Other (Assisted)'}

_POPULATION_GROUPS: dict[str, str] = {
    '0': 'Possessions',
    '1': 'Cities 250,000 or Over',
    '1A': 'Cities 1,000,000 or Over',
    '1B': 'Cities 500,000 to 999,999',
    '1C': 'Cities 250,000 to 499,999',
    '2': 'Cities 100,000 to 249,999',
    '3': 'Cities 50,000 to 99,999',
    '4': 'Cities 25,000 to 49,999',
    '5': 'Cities 10,000 to 24,999',
    '6': 'Cities 2,500 to 9,999',
    '7': 'Cities Under 2,500',
    '8': 'Non-MSA Counties',
    '8A': 'Non-MSA Counties 100,000 or Over',
    '8B': 'Non-MSA Counties 25,000 to 99,999',
    '8C': 'Non-MSA Counties 10,000 to 24,999',
    '8D': 'Non-MSA Counties Under 10,000',
    '8E': 'Non-MSA State Police',
    '9': 'MSA Counties',
    '9A': 'MSA Counties 100,000 or Over',
    '9B': 'MSA Counties 25,000 to 99,999',
    '9C': 'MSA Counties 10,000 to 24,999',
    '9D': 'MSA Counties Under 10,000',
    '9E': 'MSA State Police'}

_PROPERTIES: dict[str, str] = {
    '01': 'Aircraft',
    '02': 'Alcohol',
    '03': 'Automobiles',
    '04': 'Bicycles',
    '05': 'Buses',
    '06': 'Clothes/Furs',
    '07': 'Computer Hardware/Software',
    '08': 'Consumable Goods',
    '09': 'Credit/Debit Cards',
    '10': 'Drugs/Narcotics',
    '11': 'Drug/Narcotic Equipment',
    '12': 'Farm Equipment',
    '13': 'Firearms',
    '14': 'Gambling Equipment',
    '15': 'Heavy Construction/Industrial Equipment',
    '16': 'Household Goods',
    '17': 'Jewelry/Precious Metals/Gems',
    '18': 'Livestock',
    '19': 'Merchandise',
    '20': 'Money',
    '21': 'Negotiable Instruments',
    '22': 'Nonnegotiable Instruments',
    '23': 'Office-type Equipment',
    '24': 'Other Motor Vehicles',
    '25': 'Purses/Handbags/Wallets',
    '26': 'Radios/TVs/VCRs/DVD Players',
    '27': 'Recordings-Audio/Visual',
    '28': 'Recreational Vehicles',
    '29': 'Structures-Single Occupancy Dwellings',
    '30': 'Structures-Other Dwellings',
    '31': 'Structures-Other Commercial/Business',
    '32': 'Structures-Industrial/Manufacturing',
    '33': 'Structures-Public/Community',
    '34': 'Structures-Storage',
    '35': 'Structures-Other',
    '36': 'Tools',
    '37': 'Trucks',
    '38': 'Vehicle Parts/Accessories',
    '39': 'Watercraft',
    '41': 'Aircraft Parts/Accessories',
    '42': 'Artistic Supplies/Accessories',
    '43': 'Building Materials',
    '44': 'Camping/Hunting/Fishing Equipment/Supplies',
    '45': 'Chemicals',
    '46': 'Collections/Collectibles',
    '47': 'Crops',
    '48': 'Documents/Personal or Business',
    '49': 'Explosives',
    '59': 'Firearm Accessories',
    '64': 'Fuel',
    '65': 'Identity Documents',
    '66': 'Identity-Intangible',
    '67': 'Law Enforcement Equipment',
    '68': 'Lawn/Yard/Garden Equipment',
    '69': 'Logging Equipment',
    '70': 'Medical/Medical Lab Equipment',
    '71': 'Metals, Non-Precious',
    '72': 'Musical Instruments',
    '73': 'Pets',
    '74': 'Photographic/Optical Equipment',
    '75': 'Portable Electronic Communications',
    '76': 'Recreational/Sports Equipment',
    '77': 'Other',
    '78': 'Trailers',
    '79': 'Watercraft Equipment/Parts/Accessories',
    '80': 'Weapons-Other',
    '88': 'Pending Inventory',
    '99': 'Special Category'}

_RACES: dict[str, str] = {
    'W': 'White',
    'B': 'Black or African American',
    'I': 'American Indian or Alaska Native',
    'A': 'Asian',
    'P': 'Native Hawaiian or Other Pacific Islander',
    'M': 'Multiple',
    'U': 'Unknown'}

_REGIONS: dict[str, str] = {
    '0': 'Possessions',
    '1': 'Northeast',
    '2': 'North Central',
    '3': 'South',
    '4': 'West'}

_RELATIONSHIPS: dict[str, str] = {
    'AQ': 'Acquaintance',
    'BE': 'Babysittee',
    'BG': 'Boyfriend/Girlfriend',
    'CF': 'Child of Boyfriend/Girlfriend',
    'CH': 'Child',
    'CO': 'Cohabitant (Non-intimate)',
    'CS': 'Common-Law Spouse',
    'EE': 'Employee',
    'ER': 'Employer',
    'FC': 'Foster Child',
    'FP': 'Foster Parent',
    'FR': 'Friend',
    'GC': 'Grandchild',
    'GP': 'Grandparent',
    'HR': 'Homosexual Relationship',
    'IL': 'In-law',
    'NE': 'Neighbor',
    'OF': 'Other Family Member',
    'OK': 'Otherwise Known',
    'PA': 'Parent',
    'RU': 'Relationship Unknown',
    'SB': 'Sibling',
    'SC': 'Stepchild',
    'SE': 'Spouse',
    'SP': 'Stepparent',
    'SS': 'Stepsibling',
    'ST': 'Stranger',
    'VO': 'Victim Was Offender',
    'XR': 'Ex-Relationship (Ex-Boyfriend/Girlfriend)',
    'XS': 'Ex-Spouse'}

_RESIDENTS: dict[str, str] = {
    'R': 'Resident',
    'N': 'Nonresident',
    'U': 'Unknown'}

_SEXES: dict[str, str] = {'F': 'Female', 'M': 'Male', 'U': 'Unknown'}

_USING: dict[str, str] = {
    'A': 'Alcohol',
    'C': 'Computer Equipment',
    'D': 'Drugs/Narcotics',
    'N': 'Not Applicable',
    'R': 'Drone/Unmanned Aircraft System'}

_VICTIM_TYPES: dict[str, str] = {
    'B': 'Business',
    'F': 'Financial Institution',
    'G': 'Government',
    'I': 'Individual',
    'L': 'Law Enforcement Officer',
    'O': 'Other',
    'R': 'Religious Organization',
    'S': 'Society/Public',
    'U': 'Unknown'}

_WEAPONS: dict[str, str] = {
    '01': 'Unarmed',
    '11': 'Firearm',
    '12': 'Handgun',
    '13': 'Rifle',
    '14': 'Shotgun',
    '15': 'Other Firearm',
    '16': 'Lethal Cutting Instrument',
    '17': 'Club/Blackjack/Brass Knuckles',
    '20': 'Knife/Cutting Instrument',
    '30': 'Blunt Object',
    '35': 'Motor Vehicle/Vessel',
    '40': 'Personal Weapons',
    '50': 'Poison',
    '60': 'Explosives',
    '65': 'Fire/Incendiary Device',
    '70': 'Drugs/Narcotics/Sleeping Pills',
    '85': 'Asphyxiation',
    '90': 'Other',
    '95': 'Unknown',
    '99': 'None'}

CODEBOOKS: dict[str, Mapping[str, str]] = {
    'activities': _ACTIVITIES,
    'agency_types': _AGENCY_TYPES,
    'ages': _AGES,
    'arrest_types': _ARREST_TYPES,
    'biases': _BIASES,
    'circumstances': _CIRCUMSTANCES,
    'clearances': _CLEARANCES,
    'completions': _COMPLETIONS,
    'dispositions': _DISPOSITIONS,
    'divisions': _DIVISIONS,
    'drugs': _DRUGS,
    'entries': _ENTRIES,
    'ethnicities': _ETHNICITIES,
    'injuries': _INJURIES,
    'justifications': _JUSTIFICATIONS,
    'locations': _LOCATIONS,
    'losses': _LOSSES,
    'measures': _MEASURES,
    'multiple_arrestees': _MULTIPLE_ARRESTEES,
    'offenses': {k: v[0] for k, v in _OFFENSES.items()},
    'officer_activities': _OFFICER_ACTIVITIES,
    'officer_assignments': _OFFICER_ASSIGNMENTS,
    'population_groups': _POPULATION_GROUPS,
    'properties': _PROPERTIES,
    'races': _RACES,
    'regions': _REGIONS,
    'relationships': _RELATIONSHIPS,
    'residents': _RESIDENTS,
    'sexes': _SEXES,
    'states': STATE_NAMES,
    'using': _USING,
    'victim_types': _VICTIM_TYPES,
    'weapons': _WEAPONS}
