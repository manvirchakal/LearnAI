import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import HomeScreen from '../../app/home/HomeScreen';
import Tab1Screen from '../../app/tabs/Tab1Screen';
import Tab2Screen from '../../app/tabs/Tab2Screen';
import Tab3Screen from '../../app/tabs/Tab3Screen';

const Tab = createBottomTabNavigator();

export default function MainTabNavigator() {
  return (
    <Tab.Navigator>
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="Tab1" component={Tab1Screen} />
      <Tab.Screen name="Tab2" component={Tab2Screen} />
      <Tab.Screen name="Tab3" component={Tab3Screen} />
    </Tab.Navigator>
  );
}
