import xml.etree.ElementTree as ET
import json


itemDetailMap = ""
with open('itemDetailMap.json', 'r') as file:

    content = file.read()
    itemDetailMap = json.loads(content)

#print(itemDetailMap)
mainHand={}
for item in itemDetailMap:

    if(("equipmentDetail" in itemDetailMap[item]) and ((itemDetailMap[item]["equipmentDetail"]['type'] == "/equipment_types/main_hand") or (itemDetailMap[item]["equipmentDetail"]['type'] == "/equipment_types/two_hand"))) :
        hrid = itemDetailMap[item]['hrid']
        hrid = hrid[7:]
        mainHand[hrid] = True

topWeapon={
    "sundering_crossbow":True,
    "cursed_bow":True,
    "rippling_trident":True,
    "blazing_trident":True,
    "blooming_trident":True,
    "regal_sword":True,
    "chaotic_flail":True,
    "furious_spear":True,
    "griffin_bulwark":True
}
mainHand = topWeapon


ET.register_namespace('', "http://www.w3.org/2000/svg")  
file_xml = 'items.xml'# xml文件路径
tree = ET.parse(file_xml)
root = tree.getroot()
#for elem in root.iter():
    #print( elem.tag)

print(root.find("{http://www.w3.org/2000/svg}symbol").get("id"))
for item in root.findall("{http://www.w3.org/2000/svg}symbol"):
    id = item.get("id")
    if(id not in mainHand):
        root.remove(item)
        #print(item.get("id"))
tree.write("weapon.svg")