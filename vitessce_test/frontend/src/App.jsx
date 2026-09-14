import { Vitessce } from 'vitessce';
import myViewConfig from '../../data/Dunlap_2022/dunlap_2022_healthy_x_sle_view.json';

export default function MyApp() {
    return (
        <Vitessce
            config={myViewConfig}
            height={1800}
            theme="light"
        />
    );
}
