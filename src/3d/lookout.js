// 登上天守远望（3.37）：镜头放到城上方（地面 + 约 100 m 的真实高度 × 起伏倍数），平视四周；拖动只转方向、不平移不缩放。
// 做法：目标点就是眼睛的位置，镜头在它后面 0.05 个单位，MapControls 绕目标转 = 原地环顾。
// 建筑、树、旗在立体图里都是放大了的示意模型，远望时会挡住视线，收起来；国名、城名等标签照常（远处的山河有名字）
import * as THREE from 'three';

const EYE_M = 100; // 天守最上层离地约几十米（姬路城天守约 31 m），加上天守台与城山，取 100 m 看得远一些

export function createLookout({ camera, controls, groundY, scale, setHidden, onChange }) {
  let saved = null; // 进来之前的镜头与控制设置

  function enter(x, z) {
    if (!saved) {
      saved = {
        target: controls.target.clone(), pos: camera.position.clone(),
        min: controls.minDistance, minP: controls.minPolarAngle, maxP: controls.maxPolarAngle,
        pan: controls.enablePan, zoom: controls.enableZoom, mouse: { ...controls.mouseButtons }, touches: { ...controls.touches },
      };
    }
    const eye = groundY(x, z) + Math.max(0.06, EYE_M * scale());
    // 朝向：沿原来镜头的方位角看过去
    const off = camera.position.clone().sub(controls.target);
    const az = Math.atan2(off.x, off.z);
    controls.target.set(x, eye, z);
    camera.position.set(x + Math.sin(az) * 0.05, eye, z + Math.cos(az) * 0.05);
    controls.minDistance = 0.01;
    controls.minPolarAngle = 0.3 * Math.PI;
    controls.maxPolarAngle = 0.56 * Math.PI;
    controls.enablePan = false;
    controls.enableZoom = false;
    controls.mouseButtons = { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.ROTATE, RIGHT: THREE.MOUSE.ROTATE };
    controls.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.ROTATE };
    controls.update();
    setHidden(true);
    document.body.classList.add('lookout');
    onChange(true);
  }

  // 离开：镜头回到进来之前的地方
  function leave() {
    if (!saved) return;
    const s = saved;
    saved = null;
    controls.minDistance = s.min;
    controls.minPolarAngle = s.minP;
    controls.maxPolarAngle = s.maxP;
    controls.enablePan = s.pan;
    controls.enableZoom = s.zoom;
    controls.mouseButtons = s.mouse;
    controls.touches = s.touches;
    controls.target.copy(s.target);
    camera.position.copy(s.pos);
    controls.update();
    setHidden(false);
    document.body.classList.remove('lookout');
    onChange(false);
  }

  // 起伏倍数改了：眼睛跟着地面走
  function follow() {
    if (!saved) return;
    const t = controls.target;
    const eye = groundY(t.x, t.z) + Math.max(0.06, EYE_M * scale());
    camera.position.y += eye - t.y;
    t.y = eye;
  }

  return { enter, leave, follow, get active() { return !!saved; } };
}
